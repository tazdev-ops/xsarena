"""WebSocket logic for the XSArena Bridge API."""

import asyncio
import logging
import os
import queue
import sys
import threading
import time
from datetime import datetime
from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Global variables for WebSocket state
browser_ws: WebSocket | None = None
response_channels: Dict[str, asyncio.Queue] = {}
last_activity_time = datetime.now()
cloudflare_verified = False  # Track Cloudflare verification status per request
REFRESHING_BY_REQUEST: Dict[
    str, int
] = {}  # Per-request Cloudflare refresh attempt counter
# Queue for thread-safe communication from background threads to main thread
command_queue = queue.Queue()
idle_restart_thread = None
idle_restart_stop_event = None


async def websocket_endpoint(websocket: WebSocket, CONFIG):
    """WebSocket endpoint to handle connections from the userscript."""
    global browser_ws, REFRESHING_BY_REQUEST
    await websocket.accept()
    if browser_ws:
        logger.warning("New userscript connection received, replacing the old one.")
    browser_ws = websocket
    logger.info("✅ Userscript connected via WebSocket.")

    # Reset Cloudflare verification flag and refresh status on new connection
    global cloudflare_verified
    cloudflare_verified = False
    REFRESHING_BY_REQUEST.clear()  # Clear all per-request refresh flags

    try:
        while True:
            # Check for commands from background threads
            try:
                # Non-blocking check for commands from background threads
                cmd_type, cmd_data = command_queue.get_nowait()
                if cmd_type == "reconnect" and browser_ws:
                    await browser_ws.send_json({"command": "reconnect"})
                    logger.info("Sent reconnect command from background thread")
            except queue.Empty:
                pass  # No commands in queue, continue with normal processing

            # Receive message from userscript
            message = await websocket.receive_json()
            request_id = message.get("request_id")
            command = message.get("command")
            data = message.get("data")

            if command:
                # Handle commands from userscript
                if command == "refresh":
                    logger.info("Received refresh command from userscript")
                    # This means Cloudflare challenge was handled, reset verification flag
                    cloudflare_verified = False
                    REFRESHING_BY_REQUEST.clear()  # Clear all per-request refresh flags
                elif command == "reconnect":
                    logger.info("Received reconnect command from userscript")
                    # This means userscript wants to reconnect
                    pass
                elif command == "send_page_source":
                    # This command means userscript wants to send page source for model update
                    pass
                elif command == "activate_id_capture":
                    logger.info("Received activate_id_capture command from userscript")
                    pass
                continue

            # Handle regular data responses
            if request_id in response_channels:
                await response_channels[request_id].put(data)
            else:
                logger.warning(
                    f"Received data for unknown or closed request_id: {request_id}"
                )
    except WebSocketDisconnect:
        logger.warning("❌ Userscript disconnected.")
    finally:
        browser_ws = None
        for resp_q in response_channels.values():
            await resp_q.put({"error": "Browser disconnected."})
        response_channels.clear()


def idle_restart_worker(CONFIG):
    """Background thread to monitor idle time and restart the process if needed."""
    global last_activity_time, idle_restart_stop_event
    logger.info("Idle restart thread started")

    while not idle_restart_stop_event.is_set():
        try:
            # Check if idle restart is enabled
            enable_idle_restart = CONFIG.get("enable_idle_restart", False)
            idle_timeout = CONFIG.get(
                "idle_restart_timeout_seconds", 3600
            )  # Default 1 hour

            if enable_idle_restart and idle_timeout > 0:
                # Calculate time since last activity
                time_since_activity = (
                    datetime.now() - last_activity_time
                ).total_seconds()

                if time_since_activity > idle_timeout:
                    logger.info(
                        f"Idle timeout reached ({time_since_activity}s > {idle_timeout}s), restarting..."
                    )

                    # Put reconnect command in queue for main thread to process
                    try:
                        command_queue.put(("reconnect", None))
                        logger.info("Queued reconnect command for userscript")
                    except Exception as e:
                        logger.warning(f"Could not queue reconnect command: {e}")

                    # Sleep a bit before restart
                    time.sleep(2.5)  # Sleep 2-3 seconds as specified

                    # Restart the process
                    logger.warning(
                        "Idle restart: restarting process; active jobs may be interrupted. "
                        "Set bridge.enable_idle_restart=false to disable."
                    )
                    # Skip restart when active requests present
                    if response_channels:  # active streams present
                        idle_restart_stop_event.wait(timeout=30)
                        continue
                    os.execv(sys.executable, [sys.executable] + sys.argv)

            # Check every 30 seconds to avoid excessive CPU usage
            idle_restart_stop_event.wait(timeout=30)
        except Exception as e:
            logger.error(f"Error in idle restart worker: {e}")
            idle_restart_stop_event.wait(timeout=30)

    logger.info("Idle restart thread stopped")


def start_idle_restart_thread(CONFIG):
    """Start the idle restart background thread."""
    global idle_restart_thread, idle_restart_stop_event
    if idle_restart_thread is None or not idle_restart_thread.is_alive():
        idle_restart_stop_event = threading.Event()
        idle_restart_thread = threading.Thread(
            target=idle_restart_worker, daemon=True, args=(CONFIG,)
        )
        idle_restart_thread.start()
        logger.info("Idle restart thread started")


def stop_idle_restart_thread():
    """Stop the idle restart background thread."""
    global idle_restart_thread, idle_restart_stop_event
    if idle_restart_stop_event:
        idle_restart_stop_event.set()
    if idle_restart_thread and idle_restart_thread.is_alive():
        idle_restart_thread.join(timeout=1)
        logger.info("Idle restart thread stopped")
