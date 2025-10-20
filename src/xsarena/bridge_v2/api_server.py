# src/xsarena/bridge_v2/api_server.py
import asyncio
import hmac
import json
import logging
import os
import queue
import sys
import threading
import time
import uuid
from collections import deque
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
REFRESHING_BY_REQUEST: dict[
    str, int
] = {}  # Per-request Cloudflare refresh attempt counter
# Queue for thread-safe communication from background threads to main thread
command_queue = queue.Queue()
idle_restart_thread = None
idle_restart_stop_event = None

# Rate limiting (channel limits moved inside handler)
RATE = CONFIG.get("rate_limit", {"burst": 10, "window_seconds": 10})
PER_PEER = {}  # dict[ip] -> deque of timestamps


def _internal_ok(request: Request) -> bool:
    try:
        token = (CONFIG.get("internal_api_token") or "").strip()
        header = request.headers.get("x-internal-token", "")
        return bool(token) and hmac.compare_digest(header, token)
    except Exception:
        return False


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
            raw_data = json.loads(content) if content.strip() else {}

            # Ensure MODEL_NAME_TO_ID_MAP is dict; if a list is read, convert to {name: name}
            if isinstance(raw_data, list):
                MODEL_NAME_TO_ID_MAP = {name: name for name in raw_data}
            elif isinstance(raw_data, dict):
                MODEL_NAME_TO_ID_MAP = raw_data
            else:
                MODEL_NAME_TO_ID_MAP = {}

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
        logger.error(
            f"Failed to parse 'model_endpoint_map.json': {e}. Using empty map."
        )
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


from .payload_converter import convert_openai_to_lmarena_payload


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

# Safer default CORS: localhost-only; make configurable via CONFIG
cors_origins = CONFIG.get("cors_origins") or [
    "*"
]  # Default to ["*"] when CONFIG has no cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    global cloudflare_verified, last_activity_time, REFRESHING_BY_REQUEST
    if not browser_ws:
        raise HTTPException(status_code=503, detail="Userscript client not connected.")

    # Check channel limit
    max_channels = int(CONFIG.get("max_channels", 200))
    if len(response_channels) >= max_channels:
        raise HTTPException(status_code=503, detail="Server busy")

    # Update last activity time
    last_activity_time = datetime.now()

    # Rate limiting per peer
    peer = request.client.host or "unknown"
    now = time.time()
    if peer not in PER_PEER:
        PER_PEER[peer] = deque()
    # Prune old timestamps
    while PER_PEER[peer] and now - PER_PEER[peer][0] > RATE["window_seconds"]:
        PER_PEER[peer].popleft()
    # Check if over burst limit
    if len(PER_PEER[peer]) >= RATE["burst"]:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    # Add current timestamp
    PER_PEER[peer].append(now)

    # Check for API key if configured
    api_key = CONFIG.get("api_key")
    if api_key:
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401, detail="Missing or invalid Authorization header"
            )
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or not hmac.compare_digest(parts[1], api_key):
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
        # Initialize per-request refresh state
        REFRESHING_BY_REQUEST.pop(request_id, None)

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
            openai_req,
            session_id,
            message_id,
            model_name,
            MODEL_NAME_TO_ID_MAP,
            MODEL_ENDPOINT_MAP,
            CONFIG,
        )
        await browser_ws.send_json(
            {"request_id": request_id, "payload": lmarena_payload}
        )

        # Reset Cloudflare verification flag for this request
        cloudflare_verified = False

        async def stream_generator():
            global cloudflare_verified, REFRESHING_BY_REQUEST
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
                            # Check if this looks like a Cloudflare page using configurable patterns
                            cloudflare_patterns = CONFIG.get(
                                "cloudflare_patterns",
                                [
                                    "Just a moment...",
                                    "Enable JavaScript and cookies to continue",
                                    "Checking your browser before accessing",
                                ],
                            )
                            if any(pattern in data for pattern in cloudflare_patterns):
                                max_refresh_attempts = CONFIG.get(
                                    "max_refresh_attempts", 1
                                )
                                current_refresh_attempts = REFRESHING_BY_REQUEST.get(
                                    request_id, 0
                                )
                                if current_refresh_attempts < max_refresh_attempts:
                                    # First time seeing Cloudflare, trigger refresh
                                    logger.info(
                                        f"Detected Cloudflare challenge, sending refresh command (attempt {current_refresh_attempts + 1}/{max_refresh_attempts})"
                                    )
                                    REFRESHING_BY_REQUEST[request_id] = (
                                        current_refresh_attempts + 1
                                    )
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
                                    # Already tried refreshing up to max attempts, return error
                                    error_chunk = {
                                        "error": {
                                            "type": "cloudflare_challenge",
                                            "message": f"Cloudflare security challenge still present after {max_refresh_attempts} refresh attempts. Please manually refresh the browser.",
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
                            # Reset per-request refresh flag after successful completion
                            REFRESHING_BY_REQUEST.pop(request_id, None)
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
                # Reset per-request refresh flag in all exit paths to prevent getting stuck
                REFRESHING_BY_REQUEST.pop(request_id, None)
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
                            # Check if this looks like a Cloudflare page using configurable patterns
                            cloudflare_patterns = CONFIG.get(
                                "cloudflare_patterns",
                                [
                                    "Just a moment...",
                                    "Enable JavaScript and cookies to continue",
                                    "Checking your browser before accessing",
                                ],
                            )
                            if any(pattern in data for pattern in cloudflare_patterns):
                                max_refresh_attempts = CONFIG.get(
                                    "max_refresh_attempts", 1
                                )
                                current_refresh_attempts = REFRESHING_BY_REQUEST.get(
                                    request_id, 0
                                )
                                if current_refresh_attempts < max_refresh_attempts:
                                    # First time seeing Cloudflare, trigger refresh
                                    logger.info(
                                        f"Detected Cloudflare challenge, sending refresh command (attempt {current_refresh_attempts + 1}/{max_refresh_attempts})"
                                    )
                                    REFRESHING_BY_REQUEST[request_id] = (
                                        current_refresh_attempts + 1
                                    )
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
                                    # Already tried refreshing up to max attempts, return error
                                    raise HTTPException(
                                        status_code=503,
                                        detail=f"Cloudflare security challenge still present after {max_refresh_attempts} refresh attempts. Please manually refresh the browser.",
                                    )

                        if isinstance(data, dict) and "error" in data:
                            logger.error(f"Error from browser: {data['error']}")
                            raise HTTPException(status_code=502, detail=data["error"])
                        if data == "[DONE]":
                            # Reset per-request refresh flag after successful completion
                            REFRESHING_BY_REQUEST.pop(request_id, None)
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
                # Reset per-request refresh flag in all exit paths to prevent getting stuck
                REFRESHING_BY_REQUEST.pop(request_id, None)
                if request_id in response_channels:
                    del response_channels[request_id]
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        if request_id in response_channels:
            del response_channels[request_id]
        REFRESHING_BY_REQUEST.pop(request_id, None)
        logger.error(f"Error processing chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/start_id_capture")
async def start_id_capture(request: Request):
    if not _internal_ok(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not browser_ws:
        raise HTTPException(status_code=503, detail="Browser client not connected.")
    await browser_ws.send_json({"command": "activate_id_capture"})
    return JSONResponse({"status": "success", "message": "Activation command sent."})


@app.post("/internal/request_model_update")
async def request_model_update(request: Request):
    if not _internal_ok(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    """Request userscript to send page source for model update."""
    if not browser_ws:
        raise HTTPException(status_code=503, detail="Browser client not connected.")
    await browser_ws.send_json({"command": "send_page_source"})
    return JSONResponse({"status": "success", "message": "Page source request sent."})


@app.post("/internal/update_available_models")
async def update_available_models(request: Request):
    if not _internal_ok(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    """Update available models from HTML source."""
    try:
        # Check payload size limit
        body = await request.body()
        if len(body) > int(CONFIG.get("max_internal_post_bytes", 2_000_000)):
            raise HTTPException(status_code=413, detail="Payload too large")
        html_str = body.decode("utf-8", "replace")

        content_type = request.headers.get("content-type", "")
        if "text/html" in content_type:
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
                                # Ensure models is a dict {name: id or name} for models.json
                                if isinstance(models, list):
                                    # Convert list to dict format {name: name}
                                    models_dict = {name: name for name in models}
                                elif isinstance(models, dict):
                                    # Already in correct format
                                    models_dict = models
                                else:
                                    # If it's neither list nor dict, use empty dict
                                    models_dict = {}

                                # Save models to models.json
                                with open("models.json", "w", encoding="utf-8") as f:
                                    json.dump(models_dict, f, indent=2)
                                logger.info(
                                    f"Updated {len(models_dict)} models from HTML source"
                                )
                                return JSONResponse(
                                    {
                                        "status": "success",
                                        "message": f"Updated {len(models_dict)} models",
                                        "count": len(models_dict),
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
                        # Ensure models is a dict {name: id or name} for models.json
                        if isinstance(models, list):
                            # Convert list to dict format {name: name}
                            models_dict = {name: name for name in models}
                        elif isinstance(models, dict):
                            # Already in correct format
                            models_dict = models
                        else:
                            # If it's neither list nor dict, use empty dict
                            models_dict = {}

                        # Save models to models.json
                        with open("models.json", "w", encoding="utf-8") as f:
                            json.dump(models_dict, f, indent=2)
                        logger.info(
                            f"Updated {len(models_dict)} models from script tag"
                        )
                        return JSONResponse(
                            {
                                "status": "success",
                                "message": f"Updated {len(models_dict)} models",
                                "count": len(models_dict),
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
    if not _internal_ok(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    """Update session and message IDs from the userscript."""
    try:
        import re

        payload = await request.json()
        session_id = payload.get("sessionId") or payload.get("session_id")
        message_id = payload.get("messageId") or payload.get("message_id")

        # Validate session_id and message_id format to prevent pathologically large/evil inputs
        rx = re.compile(r"^[A-Za-z0-9_\-:.]{1,200}$")
        if not (
            session_id and message_id and rx.match(session_id) and rx.match(message_id)
        ):
            raise HTTPException(status_code=400, detail="Invalid id format")

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
            except (FileNotFoundError, yaml.YAMLError):
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
def internal_config(request: Request):
    if not _internal_ok(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
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
        for model_name in MODEL_NAME_TO_ID_MAP.keys():  # Iterate over keys
            # Try to determine if it's an image model
            try:
                with open("models.json", "r", encoding="utf-8") as f:
                    models_data = json.load(f)
                model_info = models_data.get(model_name)
                if model_info and isinstance(model_info, dict):
                    if model_info.get("type") == "image":
                        pass
            except (FileNotFoundError, json.JSONDecodeError):
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
def internal_reload(request: Request):
    if not _internal_ok(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
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
    except AttributeError:
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


def run_server():
    import os

    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("XSA_BRIDGE_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5102")),
    )


if __name__ == "__main__":
    import os

    api_port = int(os.getenv("PORT", "5102"))
    host = os.getenv("XSA_BRIDGE_HOST", "127.0.0.1")
    logger.info("🚀 LMArena Bridge v2.0 API 服务器正在启动...")
    logger.info(f"   - 监听地址: http://{host}:{api_port}")
    logger.info(f"   - WebSocket 端点: ws://{host}:{api_port}/ws")
    uvicorn.run(app, host=host, port=api_port)
