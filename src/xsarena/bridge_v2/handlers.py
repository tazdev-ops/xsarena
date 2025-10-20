"""Request handlers for the XSArena Bridge API."""

import asyncio
import hmac
import json
import logging
import time
import uuid
from collections import deque
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .payload_converter import convert_openai_to_lmarena_payload

logger = logging.getLogger(__name__)

# Global configuration
CONFIG = {}
MODEL_NAME_TO_ID_MAP = {}
MODEL_ENDPOINT_MAP = {}
RATE = CONFIG.get("rate_limit", {"burst": 10, "window_seconds": 10})
PER_PEER = {}  # dict[ip] -> deque of timestamps


def _internal_ok(request: Request) -> bool:
    """Check if request has valid internal API token."""
    try:
        token = (CONFIG.get("internal_api_token") or "").strip()
        header = request.headers.get("x-internal-token", "")
        return bool(token) and hmac.compare_digest(header, token)
    except Exception:
        return False


def load_config():
    """Load configuration from .xsarena/config.yml."""
    global CONFIG
    # Load config from .xsarena/config.yml first
    try:
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
    """Load model mappings from models.json."""
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
    """Load model endpoint mappings from model_endpoint_map.json."""
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


async def chat_completions_handler(
    request: Request,
    browser_ws,
    response_channels,
    REFRESHING_BY_REQUEST,
    cloudflare_verified,
):
    """Handle chat completions requests."""
    if not browser_ws:
        raise HTTPException(status_code=503, detail="Userscript client not connected.")

    # Check channel limit
    max_channels = int(CONFIG.get("max_channels", 200))
    if len(response_channels) >= max_channels:
        raise HTTPException(status_code=503, detail="Server busy")

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
                            from .api_server import format_openai_finish_chunk

                            yield format_openai_finish_chunk(
                                model_name, request_id, reason="stop"
                            )
                            # Reset per-request refresh flag after successful completion
                            REFRESHING_BY_REQUEST.pop(request_id, None)
                            break

                        # Handle image content for image models
                        if isinstance(data, str) and data.startswith("![Image]"):
                            # This is an image markdown, format as appropriate
                            from .api_server import format_openai_chunk

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


async def update_available_models_handler(request: Request):
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


async def update_id_capture_handler(request: Request):
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
