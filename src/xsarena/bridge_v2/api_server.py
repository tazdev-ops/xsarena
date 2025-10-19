# src/xsarena/bridge_v2/api_server.py
import asyncio
import json
import logging
import os
import queue
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

browser_ws: WebSocket | None = None
response_channels: dict[str, asyncio.Queue] = {}
CONFIG = {}
MODEL_NAME_TO_ID_MAP = {}
MODEL_ENDPOINT_MAP = {}
last_activity_time = datetime.now()
cloudflare_verified = False  # Track Cloudflare verification status per request
IS_REFRESHING_FOR_VERIFICATION = False  # Global flag for Cloudflare refresh status
# Queue for thread-safe communication from background threads to main thread
command_queue = queue.Queue()
idle_restart_thread = None
idle_restart_stop_event = None


def _parse_jsonc(jsonc_string: str) -> dict:
    lines = [
        line for line in jsonc_string.splitlines() if not line.strip().startswith("//")
    ]
    return json.loads("\n".join(lines))


def load_config():
    global CONFIG
    # Load config from .xsarena/config.yml first
    try:
        from pathlib import Path

        import yaml

        yaml_config_path = Path(".xsarena/config.yml")
        if yaml_config_path.exists():
            with open(yaml_config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f) or {}
            # Extract bridge config if present, otherwise use the whole config
            CONFIG = yaml_config.get("bridge", yaml_config)
            logger.info(f"Successfully loaded configuration from '{yaml_config_path}'.")

    except Exception as e:
        logger.error(
            f"Failed to load configuration: {e}. Please run 'xsarena project config-migrate'"
        )
        CONFIG = {}


def load_model_map():
    global MODEL_NAME_TO_ID_MAP
    try:
        with open("models.json", "r", encoding="utf-8") as f:
            content = f.read()
            MODEL_NAME_TO_ID_MAP = json.loads(content) if content.strip() else {}
        logger.info(
            f"Successfully loaded {len(MODEL_NAME_TO_ID_MAP)} models from 'models.json'."
        )
    except FileNotFoundError:
        logger.warning("models.json not found. Using empty model list.")
        MODEL_NAME_TO_ID_MAP = {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse 'models.json': {e}. Using empty model list.")
        MODEL_NAME_TO_ID_MAP = {}
    except Exception as e:
        logger.error(f"Failed to load 'models.json': {e}. Using empty model list.")
        MODEL_NAME_TO_ID_MAP = {}


def load_model_endpoint_map():
    global MODEL_ENDPOINT_MAP
    try:
        with open("model_endpoint_map.json", "r", encoding="utf-8") as f:
            content = f.read()
            MODEL_ENDPOINT_MAP = json.loads(content) if content.strip() else {}
        logger.info(
            f"Successfully loaded {len(MODEL_ENDPOINT_MAP)} model endpoint mappings."
        )
    except FileNotFoundError:
        logger.warning("model_endpoint_map.json not found. Using empty map.")
        MODEL_ENDPOINT_MAP = {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse 'model_endpoint_map.json': {e}. Using empty map.")
        MODEL_ENDPOINT_MAP = {}
    except Exception as e:
        logger.error(f"Failed to load 'model_endpoint_map.json': {e}. Using empty map.")
        MODEL_ENDPOINT_MAP = {}


def idle_restart_worker():
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
                    logger.info("Restarting process...")
                    os.execv(sys.executable, [sys.executable] + sys.argv)

            # Check every 30 seconds to avoid excessive CPU usage
            idle_restart_stop_event.wait(timeout=30)
        except Exception as e:
            logger.error(f"Error in idle restart worker: {e}")
            idle_restart_stop_event.wait(timeout=30)

    logger.info("Idle restart thread stopped")


def start_idle_restart_thread():
    """Start the idle restart background thread."""
    global idle_restart_thread, idle_restart_stop_event
    if idle_restart_thread is None or not idle_restart_thread.is_alive():
        idle_restart_stop_event = threading.Event()
        idle_restart_thread = threading.Thread(target=idle_restart_worker, daemon=True)
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


async def _process_openai_message(message: dict) -> dict:
    content = message.get("content")
    role = message.get("role")
    text_content = ""

    # Text-only processing: only accept string content, ignore any content lists
    if isinstance(content, list):
        # For text-only mode, ignore all list content (attachments, images)
        text_content = ""
    elif isinstance(content, str):
        text_content = content

    if role == "user" and not (text_content or "").strip():
        text_content = " "

    return {
        "role": role,
        "content": text_content,
        "attachments": [],  # always empty; images disabled
    }


async def convert_openai_to_lmarena_payload(
    openai_data: dict, session_id: str, message_id: str, model_name: str
) -> dict:
    messages = openai_data.get("messages", [])

    target_model_id = MODEL_NAME_TO_ID_MAP.get(model_name)

    # Handle role mapping: merge 'developer' role into 'system'
    processed_messages = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        # Map 'developer' role to 'system'
        if role == "developer":
            role = "system"

        processed_messages.append({"role": role, "content": content})

    # Determine mode and target from per-model mapping or config
    mode = "direct_chat"  # default
    battle_target = "a"  # default

    # Check if model has specific endpoint mapping with mode/battle_target
    if model_name in MODEL_ENDPOINT_MAP:
        endpoint_config = MODEL_ENDPOINT_MAP[model_name]
        if isinstance(endpoint_config, list):
            # If it's a list, pick randomly
            import random

            endpoint_config = random.choice(endpoint_config)

        if isinstance(endpoint_config, dict):
            # Prefer mapping values if provided
            if "mode" in endpoint_config and endpoint_config["mode"] is not None:
                mode = endpoint_config["mode"]
            if (
                "battle_target" in endpoint_config
                and endpoint_config["battle_target"] is not None
            ):
                battle_target = endpoint_config["battle_target"]

    # If not set by mapping, read from config keys
    if mode == "direct_chat":  # Only update if still default
        config_mode = CONFIG.get("id_updater_last_mode")
        if config_mode:
            mode = config_mode

    if battle_target == "a":  # Only update if still default
        config_battle_target = CONFIG.get("id_updater_battle_target")
        if config_battle_target:
            battle_target = config_battle_target

    # Apply tavern mode logic if enabled
    tavern_mode_enabled = CONFIG.get("tavern_mode_enabled", False)
    bypass_enabled = CONFIG.get("bypass_enabled", False)

    # Separate messages by role for processing
    system_messages = []
    user_messages = []
    assistant_messages = []

    for msg in processed_messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_messages.append(
                content if isinstance(content, str) else str(content)
            )
        elif role == "user":
            user_messages.append(content if isinstance(content, str) else str(content))
        elif role == "assistant":
            assistant_messages.append(
                content if isinstance(content, str) else str(content)
            )

    # If tavern mode enabled, merge multiple system messages
    final_messages = []

    if system_messages:
        if tavern_mode_enabled:
            # Merge all system messages into one
            merged_system_content = "\n\n".join(system_messages)
            system_message = {
                "role": "system",
                "content": merged_system_content,
            }
        else:
            # Just use the last system message
            system_message = {
                "role": "system",
                "content": system_messages[-1] if system_messages else "",
            }

        # Determine participantPosition for system message based on mode
        if mode == "direct_chat":
            system_message["participantPosition"] = "b"
        elif mode == "battle":
            # In battle mode, system gets the battle_target position
            system_message["participantPosition"] = battle_target
        else:
            # Default to 'a' if mode is unknown
            system_message["participantPosition"] = "a"

        final_messages.append(system_message)

    # Process remaining messages with proper participantPosition based on mode
    for msg in processed_messages:
        role = msg["role"]
        content = msg["content"]

        # Skip system messages since we already handled them above
        if role == "system":
            continue

        message_obj = {"role": role, "content": content}

        # Determine participantPosition based on mode
        if mode == "direct_chat":
            message_obj[
                "participantPosition"
            ] = "a"  # non-system in direct mode gets 'a'
        elif mode == "battle":
            # In battle mode, all messages get the battle_target position
            message_obj["participantPosition"] = battle_target
        else:
            # Default to 'a' if mode is unknown
            message_obj["participantPosition"] = "a"

        final_messages.append(message_obj)

    # Apply bypass mode if enabled and for text models
    is_image_request = False
    # Check if this is an image request based on models.json
    if model_name in MODEL_NAME_TO_ID_MAP:
        try:
            with open("models.json", "r", encoding="utf-8") as f:
                models_data = json.load(f)
            model_info = models_data.get(model_name)
            if model_info and isinstance(model_info, dict):
                if model_info.get("type") == "image":
                    is_image_request = True
        except:
            pass

    # First-message guard: if the first message is an assistant message, insert a fake user message
    if final_messages and final_messages[0]["role"] == "assistant":
        # Insert a fake user message at the beginning
        final_messages.insert(
            0,
            {
                "role": "user",
                "content": "Hi",
                "participantPosition": final_messages[0].get(
                    "participantPosition", "a"
                ),
            },
        )

    # If bypass mode is enabled and this is a text model, append a trailing user message
    if bypass_enabled and not is_image_request:
        final_messages.append(
            {"role": "user", "content": " ", "participantPosition": "a"}
        )

    return {
        "message_templates": final_messages,
        "target_model_id": target_model_id,
        "session_id": session_id,
        "message_id": message_id,
        "is_image_request": is_image_request,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    load_model_map()
    load_model_endpoint_map()
    start_idle_restart_thread()  # Start idle restart thread
    logger.info("Server startup complete. Waiting for userscript connection...")
    yield
    stop_idle_restart_thread()  # Stop idle restart thread
    logger.info("Server shutting down.")


app = FastAPI(lifespan=lifespan)

# Load allowed origins from config, default to secure localhost-only if not configured
# Note: This config is loaded in the lifespan function, but CORS is set at import time.
# For a truly dynamic solution, we'd need a custom middleware, but for now we use secure defaults.
allowed_origins = ["http://localhost", "http://127.0.0.1", "http://0.0.0.0"]  # Default to secure

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global browser_ws, IS_REFRESHING_FOR_VERIFICATION
    await websocket.accept()
    if browser_ws:
        logger.warning("New userscript connection received, replacing the old one.")
    browser_ws = websocket
    logger.info("✅ Userscript connected via WebSocket.")

    # Reset Cloudflare verification flag and refresh status on new connection
    global cloudflare_verified
    cloudflare_verified = False
    IS_REFRESHING_FOR_VERIFICATION = False

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
                    IS_REFRESHING_FOR_VERIFICATION = False
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
        for queue in response_channels.values():
            await queue.put({"error": "Browser disconnected."})
        response_channels.clear()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    global cloudflare_verified, last_activity_time, IS_REFRESHING_FOR_VERIFICATION
    if not browser_ws:
        raise HTTPException(status_code=503, detail="Userscript client not connected.")

    # Update last activity time
    last_activity_time = datetime.now()

    # Check for API key if configured
    api_key = CONFIG.get("api_key")
    if api_key:
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401, detail="Missing or invalid Authorization header"
            )
        if auth_header.split(" ")[1] != api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    openai_req = await request.json()
    want_stream = bool(openai_req.get("stream"))
    model_name = openai_req.get("model", "unknown")

    # Get session and message IDs - first try job-specific IDs from payload
    session_id = None
    message_id = None

    # Check if the payload contains specific bridge IDs (from RunSpecV2)
    if "bridge_session_id" in openai_req:
        session_id = openai_req.get("bridge_session_id")
    if "bridge_message_id" in openai_req:
        message_id = openai_req.get("bridge_message_id")

    # If no job-specific IDs, then try model endpoint mapping
    if not session_id or not message_id:
        # Check if model has specific endpoint mapping
        if model_name in MODEL_ENDPOINT_MAP:
            endpoint_config = MODEL_ENDPOINT_MAP[model_name]
            if isinstance(endpoint_config, list):
                # If it's a list, pick randomly
                import random

                endpoint_config = random.choice(endpoint_config)

            if isinstance(endpoint_config, dict):
                session_id = endpoint_config.get("session_id")
                message_id = endpoint_config.get("message_id")

        # If no mapping found or mapping doesn't have IDs, use global config
        if not session_id or not message_id:
            session_id = CONFIG.get("session_id")
            message_id = CONFIG.get("message_id")

            # If still no IDs and use_default_ids_if_mapping_not_found is true, use defaults
            use_default = CONFIG.get("use_default_ids_if_mapping_not_found", True)
            if not session_id or not message_id and not use_default:
                raise HTTPException(
                    status_code=400,
                    detail="Session ID/Message ID not configured and mapping not found.",
                )

    if not session_id or not message_id:
        raise HTTPException(
            status_code=400, detail="Session ID/Message ID not configured."
        )

    request_id = str(uuid.uuid4())
    response_channels[request_id] = asyncio.Queue()

    try:
        # Process attachments if file_bed_enabled
        file_bed_enabled = CONFIG.get("file_bed_enabled", False)
        if file_bed_enabled and "messages" in openai_req:
            for message in openai_req["messages"]:
                if isinstance(message.get("content"), str):
                    # Simple check for data URLs that might be images
                    import re

                    data_url_pattern = r"data:image/[^;]+;base64,([a-zA-Z0-9+/=]+)"
                    matches = re.findall(data_url_pattern, message["content"])
                    if matches and CONFIG.get("file_bed_upload_url"):
                        # For now, we'll just log that we found data URLs
                        # In a real implementation, we'd upload to file bed
                        logger.info(
                            f"Found {len(matches)} data URLs in message content"
                        )

        lmarena_payload = await convert_openai_to_lmarena_payload(
            openai_req, session_id, message_id, model_name
        )
        await browser_ws.send_json(
            {"request_id": request_id, "payload": lmarena_payload}
        )

        # Reset Cloudflare verification flag for this request
        cloudflare_verified = False

        async def stream_generator():
            global cloudflare_verified, IS_REFRESHING_FOR_VERIFICATION
            try:
                queue = response_channels[request_id]
                timeout_seconds = CONFIG.get("stream_response_timeout_seconds", 360)

                while True:
                    try:
                        # Use timeout for queue.get to handle timeouts gracefully
                        data = await asyncio.wait_for(
                            queue.get(), timeout=timeout_seconds
                        )

                        # Check for Cloudflare detection
                        if isinstance(data, str):
                            # Check if this looks like a Cloudflare page
                            if (
                                "Just a moment..." in data
                                or "Enable JavaScript and cookies to continue" in data
                                or "Checking your browser before accessing" in data
                            ):
                                if not IS_REFRESHING_FOR_VERIFICATION:
                                    # First time seeing Cloudflare, trigger refresh
                                    logger.info(
                                        "Detected Cloudflare challenge, sending refresh command"
                                    )
                                    IS_REFRESHING_FOR_VERIFICATION = True
                                    await browser_ws.send_json({"command": "refresh"})
                                    # Wait for a short backoff period before retrying
                                    await asyncio.sleep(5.0)  # 5 second backoff
                                    # Retry by sending the same request again
                                    await browser_ws.send_json(
                                        {
                                            "request_id": request_id,
                                            "payload": lmarena_payload,
                                        }
                                    )
                                    continue  # Continue to wait for response again
                                else:
                                    # Already tried refreshing, return error
                                    error_chunk = {
                                        "error": {
                                            "type": "cloudflare_challenge",
                                            "message": "Cloudflare security challenge still present after refresh. Please manually refresh the browser.",
                                        }
                                    }
                                    yield f"data: {json.dumps(error_chunk)}\n\n"
                                    yield "data: [DONE]\n\n"
                                    break

                        if isinstance(data, dict) and "error" in data:
                            logger.error(f"Error from browser: {data['error']}")
                            raise HTTPException(status_code=502, detail=data["error"])
                        if data == "[DONE]":
                            # Check if we need to add content filter explanation in the final chunk
                            yield format_openai_finish_chunk(
                                model_name, request_id, reason="stop"
                            )
                            # Reset the refresh flag after successful completion
                            IS_REFRESHING_FOR_VERIFICATION = False
                            break

                        # Handle image content for image models
                        if isinstance(data, str) and data.startswith("![Image]"):
                            # This is an image markdown, format as appropriate
                            yield format_openai_chunk(data, model_name, request_id)
                        else:
                            yield format_openai_chunk(data, model_name, request_id)
                    except asyncio.TimeoutError:
                        logger.error(
                            f"Timeout waiting for response for request_id: {request_id}"
                        )
                        error_chunk = {
                            "error": {
                                "type": "timeout",
                                "message": f"Response timeout after {timeout_seconds} seconds",
                            }
                        }
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        break
            finally:
                # Reset the refresh flag in all exit paths to prevent getting stuck
                IS_REFRESHING_FOR_VERIFICATION = False
                if request_id in response_channels:
                    del response_channels[request_id]

        if want_stream:
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            # Aggregate into a single JSON response (OpenAI-style)
            try:
                queue = response_channels[request_id]
                timeout_seconds = CONFIG.get("stream_response_timeout_seconds", 360)
                content_parts = []

                while True:
                    try:
                        data = await asyncio.wait_for(
                            queue.get(), timeout=timeout_seconds
                        )

                        # Check for Cloudflare detection
                        if isinstance(data, str):
                            # Check if this looks like a Cloudflare page
                            if (
                                "Just a moment..." in data
                                or "Enable JavaScript and cookies to continue" in data
                                or "Checking your browser before accessing" in data
                            ):
                                if not IS_REFRESHING_FOR_VERIFICATION:
                                    # First time seeing Cloudflare, trigger refresh
                                    logger.info(
                                        "Detected Cloudflare challenge, sending refresh command"
                                    )
                                    IS_REFRESHING_FOR_VERIFICATION = True
                                    await browser_ws.send_json({"command": "refresh"})
                                    # Wait for a short backoff period before retrying
                                    await asyncio.sleep(5.0)  # 5 second backoff
                                    # Retry by sending the same request again
                                    await browser_ws.send_json(
                                        {
                                            "request_id": request_id,
                                            "payload": lmarena_payload,
                                        }
                                    )
                                    # Clear the content parts and continue waiting for the new response
                                    content_parts = []
                                    continue  # Continue to wait for response again
                                else:
                                    # Already tried refreshing, return error
                                    raise HTTPException(
                                        status_code=503,
                                        detail="Cloudflare security challenge still present after refresh. Please manually refresh the browser.",
                                    )

                        if isinstance(data, dict) and "error" in data:
                            logger.error(f"Error from browser: {data['error']}")
                            raise HTTPException(status_code=502, detail=data["error"])
                        if data == "[DONE]":
                            # Reset the refresh flag after successful completion
                            IS_REFRESHING_FOR_VERIFICATION = False
                            break
                        content_parts.append(str(data))
                    except asyncio.TimeoutError:
                        logger.error(
                            f"Timeout waiting for response for request_id: {request_id}"
                        )
                        raise HTTPException(
                            status_code=408,
                            detail=f"Response timeout after {timeout_seconds} seconds",
                        )

                content = "".join(content_parts)

                # Check if this looks like a content filter response
                finish_reason = "stop"
                if any(
                    phrase in content.lower()
                    for phrase in [
                        "content filter",
                        "filtered",
                        "inappropriate",
                        "not allowed",
                    ]
                ):
                    finish_reason = "content_filter"
                    # Add explanation for content filter
                    content += "\n\nResponse was truncated (filter/limit). Consider reducing length or simplifying."

                # Create full OpenAI ChatCompletion response
                response = {
                    "id": request_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": finish_reason,
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 0,  # Not calculated in this implementation
                        "completion_tokens": 0,  # Not calculated in this implementation
                        "total_tokens": 0,  # Not calculated in this implementation
                    },
                }
                return JSONResponse(response)
            finally:
                # Reset the refresh flag in all exit paths to prevent getting stuck
                IS_REFRESHING_FOR_VERIFICATION = False
                if request_id in response_channels:
                    del response_channels[request_id]
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        if request_id in response_channels:
            del response_channels[request_id]
        logger.error(f"Error processing chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/start_id_capture")
async def start_id_capture():
    if not browser_ws:
        raise HTTPException(status_code=503, detail="Browser client not connected.")
    await browser_ws.send_json({"command": "activate_id_capture"})
    return JSONResponse({"status": "success", "message": "Activation command sent."})


@app.post("/internal/request_model_update")
async def request_model_update():
    """Request userscript to send page source for model update."""
    if not browser_ws:
        raise HTTPException(status_code=503, detail="Browser client not connected.")
    await browser_ws.send_json({"command": "send_page_source"})
    return JSONResponse({"status": "success", "message": "Page source request sent."})


@app.post("/internal/update_available_models")
async def update_available_models(request: Request):
    """Update available models from HTML source."""
    try:
        content_type = request.headers.get("content-type", "")
        if "text/html" in content_type:
            html_content = await request.body()
            html_str = html_content.decode("utf-8")

            # Extract models from HTML - find the JSON part containing models
            import re

            # Look for the models JSON in the HTML
            pattern = r'(\{.*?"models".*?\})'
            matches = re.findall(pattern, html_str, re.DOTALL)

            if matches:
                # Try to find the actual models JSON by looking for the specific structure
                for match in matches:
                    try:
                        # Clean up the JSON string
                        cleaned_match = match.strip()
                        if cleaned_match.startswith("{") and cleaned_match.endswith(
                            "}"
                        ):
                            # Parse and extract models
                            parsed = json.loads(cleaned_match)
                            if "models" in parsed:
                                models = parsed["models"]
                                # Save models to models.json
                                with open("models.json", "w", encoding="utf-8") as f:
                                    json.dump(models, f, indent=2)
                                logger.info(
                                    f"Updated {len(models)} models from HTML source"
                                )
                                return JSONResponse(
                                    {
                                        "status": "success",
                                        "message": f"Updated {len(models)} models",
                                        "count": len(models),
                                    }
                                )
                    except json.JSONDecodeError:
                        continue

            # Alternative: look for model data in script tags or other JSON structures
            # Look for JSON within script tags
            script_pattern = (
                r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>'
            )
            script_matches = re.findall(script_pattern, html_str, re.DOTALL)

            for script_content in script_matches:
                try:
                    parsed = json.loads(script_content)
                    if "models" in parsed:
                        models = parsed["models"]
                        # Save models to models.json
                        with open("models.json", "w", encoding="utf-8") as f:
                            json.dump(models, f, indent=2)
                        logger.info(f"Updated {len(models)} models from script tag")
                        return JSONResponse(
                            {
                                "status": "success",
                                "message": f"Updated {len(models)} models",
                                "count": len(models),
                            }
                        )
                except json.JSONDecodeError:
                    continue

            # If no models found, return error
            return JSONResponse(
                {"status": "error", "message": "No models found in HTML source"}
            )
        else:
            raise HTTPException(
                status_code=400, detail="Content-Type must be text/html"
            )
    except Exception as e:
        logger.error(f"Error updating models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/id_capture/update")
async def update_id_capture(request: Request):
    """Update session and message IDs from the userscript."""
    try:
        payload = await request.json()
        session_id = payload.get("sessionId") or payload.get("session_id")
        message_id = payload.get("messageId") or payload.get("message_id")

        if not session_id or not message_id:
            raise HTTPException(
                status_code=400, detail="sessionId and messageId are required"
            )

        # Update the global CONFIG
        CONFIG["session_id"] = session_id
        CONFIG["message_id"] = message_id

        # Also save to the config file
        from pathlib import Path

        import yaml

        config_path = Path(".xsarena/config.yml")
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config if it exists
        existing_config = {}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    existing_config = yaml.safe_load(f) or {}
            except:
                pass  # If config file is invalid, start with empty dict

        # Update the bridge section with the new IDs
        if "bridge" not in existing_config:
            existing_config["bridge"] = {}
        existing_config["bridge"]["session_id"] = session_id
        existing_config["bridge"]["message_id"] = message_id

        # Save the updated config
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                existing_config, f, default_flow_style=False, sort_keys=False
            )

        logger.info(f"Updated session_id: {session_id}, message_id: {message_id}")
        return JSONResponse(
            {
                "status": "success",
                "message": "IDs updated successfully",
                "session_id": session_id,
                "message_id": message_id,
            }
        )
    except Exception as e:
        logger.error(f"Error updating ID capture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# XSArena cockpit uses this to confirm IDs after capture
@app.get("/internal/config")
def internal_config():
    return {
        "bridge": {
            "session_id": CONFIG.get("session_id"),
            "message_id": CONFIG.get("message_id"),
        },
        "tavern_mode_enabled": CONFIG.get("tavern_mode_enabled", False),
        "bypass_enabled": CONFIG.get("bypass_enabled", False),
        "file_bed_enabled": CONFIG.get("file_bed_enabled", False),
        "enable_idle_restart": CONFIG.get("enable_idle_restart", False),
        "idle_restart_timeout_seconds": CONFIG.get(
            "idle_restart_timeout_seconds", 3600
        ),
        "stream_response_timeout_seconds": CONFIG.get(
            "stream_response_timeout_seconds", 360
        ),
        "api_key_set": bool(CONFIG.get("api_key")),
    }


@app.get("/v1/models")
async def list_models():
    """Return available models in OpenAI schema."""
    try:
        models_list = []
        for model_name, _model_id in MODEL_NAME_TO_ID_MAP.items():
            # Try to determine if it's an image model
            try:
                with open("models.json", "r", encoding="utf-8") as f:
                    models_data = json.load(f)
                model_info = models_data.get(model_name)
                if model_info and isinstance(model_info, dict):
                    if model_info.get("type") == "image":
                        pass
            except:
                pass  # If models.json doesn't exist, continue with is_image_model = False

            model_obj = {
                "id": model_name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "user",
            }
            models_list.append(model_obj)

        return {"object": "list", "data": models_list}
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def format_openai_chunk(content, model, request_id):
    """Format a text chunk as an OpenAI SSE chunk."""
    # Check if this is an image markdown
    if isinstance(content, str) and content.startswith("![Image]("):
        # For image content, we'll include it as content but may need special handling
        chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {"index": 0, "delta": {"content": content}, "finish_reason": None}
            ],
        }
    else:
        chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {"index": 0, "delta": {"content": str(content)}, "finish_reason": None}
            ],
        }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def format_openai_finish_chunk(model, request_id, reason="stop"):
    """Format a finish chunk as an OpenAI SSE chunk."""
    chunk = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": reason}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


@app.post("/internal/reload")
def internal_reload():
    try:
        load_config()
        load_model_map()
        load_model_endpoint_map()
        return JSONResponse(
            {"ok": True, "reloaded": True, "version": CONFIG.get("version")}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reload failed: {e}")


def add_content_filter_explanation(content, finish_reason):
    """Add explanation for content-filter finish reason."""
    if finish_reason == "content_filter":
        return (
            content
            + "\n\nResponse was truncated (filter/limit). Consider reducing length or simplifying."
        )
    return content





# Health endpoint expected by XSArena
@app.get("/health")
def health():
    global last_activity_time
    try:
        # Try to get last_activity_time, default to None if not defined yet
        last_activity_iso = (
            last_activity_time.isoformat() if last_activity_time else None
        )
    except:
        last_activity_iso = None

    return {
        "status": "ok",
        "ts": datetime.now().isoformat(),
        "ws_connected": browser_ws is not None,
        "last_activity": last_activity_iso,
        "version": CONFIG.get("version", "unknown"),
    }


# API endpoints for jobs
@app.get("/api/jobs")
async def api_list_jobs():
    """API endpoint to list all jobs."""
    from .job_service import JobService

    job_service = JobService()
    jobs = job_service.list_jobs()

    return {"jobs": jobs}


@app.get("/api/jobs/{job_id}")
async def api_get_job(job_id: str):
    """API endpoint to get a specific job's status."""
    from .job_service import JobService

    job_service = JobService()
    job_data = job_service.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_data


# Console endpoint - serves static HTML
@app.get("/console")
async def console():
    """Serve the minimal web console HTML page."""
    from pathlib import Path
    from fastapi.responses import HTMLResponse

    console_html_path = Path(__file__).parent / "static" / "console.html"
    return HTMLResponse(content=console_html_path.read_text(encoding="utf-8"))


# Alias under v1/ for some clients
@app.get("/v1/health")
def v1_health():
    return health()


if __name__ == "__main__":
    import os

    api_port = int(os.getenv("PORT", "5102"))
    logger.info("🚀 LMArena Bridge v2.0 API 服务器正在启动...")
    logger.info(f"   - 监听地址: http://0.0.0.0:{api_port}")
    logger.info(f"   - WebSocket 端点: ws://0.0.0.0:{api_port}/ws")
    uvicorn.run(app, host="0.0.0.0", port=api_port)
