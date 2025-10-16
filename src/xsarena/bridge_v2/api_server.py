# src/xsarena/bridge_v2/api_server.py
import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

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


def _parse_jsonc(jsonc_string: str) -> dict:
    lines = [
        line for line in jsonc_string.splitlines() if not line.strip().startswith("//")
    ]
    return json.loads("\n".join(lines))


def load_config():
    global CONFIG
    # Try .xsarena/config.yml first, then fall back to JSONC files
    try:
        from pathlib import Path

        import yaml

        yaml_config_path = Path(".xsarena/config.yml")
        if yaml_config_path.exists():
            with open(yaml_config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f) or {}
            # Extract bridge config if present
            CONFIG = yaml_config.get("bridge", {})
            logger.info(f"Successfully loaded configuration from '{yaml_config_path}'.")
        else:
            # Fallback to original JSONC loading
            with open("config.jsonc", "r", encoding="utf-8") as f:
                CONFIG = _parse_jsonc(f.read())
            logger.info("Successfully loaded configuration from 'config.jsonc'.")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}. Using default config.")
        CONFIG = {}


def load_model_map():
    global MODEL_NAME_TO_ID_MAP
    try:
        with open("models.json", "r", encoding="utf-8") as f:
            MODEL_NAME_TO_ID_MAP = json.load(f)
        logger.info(
            f"Successfully loaded {len(MODEL_NAME_TO_ID_MAP)} models from 'models.json'."
        )
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
    except Exception as e:
        logger.error(f"Failed to load 'model_endpoint_map.json': {e}. Using empty map.")
        MODEL_ENDPOINT_MAP = {}


async def convert_openai_to_lmarena_payload(
    openai_data: dict, session_id: str, message_id: str
) -> dict:
    messages = openai_data.get("messages", [])
    for msg in messages:
        if msg.get("role") == "developer":
            msg["role"] = "system"

    if CONFIG.get("tavern_mode_enabled"):
        system_prompts = "\n\n".join(
            [msg["content"] for msg in messages if msg["role"] == "system"]
        )
        other_messages = [msg for msg in messages if msg["role"] != "system"]
        messages = (
            [{"role": "system", "content": system_prompts}] if system_prompts else []
        ) + other_messages

    model_name = openai_data.get("model", "default")
    target_model_id = MODEL_NAME_TO_ID_MAP.get(model_name)

    message_templates = []
    for msg in messages:
        message_templates.append(
            {
                "role": msg["role"],
                "content": msg.get("content", " "),
                "attachments": msg.get("attachments", []),
            }
        )

    mode = CONFIG.get("id_updater_last_mode", "direct_chat")
    target_participant = CONFIG.get("id_updater_battle_target", "A").lower()

    for msg in message_templates:
        if msg["role"] == "system":
            msg["participantPosition"] = (
                "b" if mode == "direct_chat" else target_participant
            )
        else:
            msg["participantPosition"] = (
                "a" if mode == "direct_chat" else target_participant
            )

    return {
        "message_templates": message_templates,
        "target_model_id": target_model_id,
        "session_id": session_id,
        "message_id": message_id,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    load_model_map()
    load_model_endpoint_map()
    logger.info("Server startup complete. Waiting for userscript connection...")
    yield
    logger.info("Server shutting down.")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global browser_ws
    await websocket.accept()
    if browser_ws:
        logger.warning("New userscript connection received, replacing the old one.")
    browser_ws = websocket
    logger.info("✅ Userscript connected via WebSocket.")
    try:
        while True:
            message = await websocket.receive_json()
            request_id = message.get("request_id")
            data = message.get("data")
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
    if not browser_ws:
        raise HTTPException(status_code=503, detail="Userscript client not connected.")

    openai_req = await request.json()
    want_stream = bool(openai_req.get("stream"))
    model_name = openai_req.get("model")

    session_id, message_id = None, None
    if model_name in MODEL_ENDPOINT_MAP:
        mapping = MODEL_ENDPOINT_MAP[model_name]
        session_id = mapping.get("session_id")
        message_id = mapping.get("message_id")

    if not session_id:
        session_id = CONFIG.get("session_id")
        message_id = CONFIG.get("message_id")

    if not session_id or not message_id:
        raise HTTPException(
            status_code=400, detail="Session ID/Message ID not configured."
        )

    request_id = str(uuid.uuid4())
    response_channels[request_id] = asyncio.Queue()

    try:
        lmarena_payload = await convert_openai_to_lmarena_payload(
            openai_req, session_id, message_id
        )
        await browser_ws.send_json(
            {"request_id": request_id, "payload": lmarena_payload}
        )

        async def stream_generator():
            try:
                queue = response_channels[request_id]
                while True:
                    data = await queue.get()
                    if isinstance(data, dict) and "error" in data:
                        logger.error(f"Error from browser: {data['error']}")
                        raise HTTPException(status_code=502, detail=data["error"])
                    if data == "[DONE]":
                        break
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': data}}]})}\n\n"
            finally:
                yield "data: [DONE]\n\n"
                if request_id in response_channels:
                    del response_channels[request_id]

        if want_stream:
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            # Aggregate into a single JSON response (OpenAI-style)
            try:
                queue = response_channels[request_id]
                content_parts = []
                while True:
                    data = await queue.get()
                    if isinstance(data, dict) and "error" in data:
                        logger.error(f"Error from browser: {data['error']}")
                        raise HTTPException(status_code=502, detail=data["error"])
                    if data == "[DONE]":
                        break
                    content_parts.append(str(data))
                content = "".join(content_parts)
                return JSONResponse({"choices": [{"message": {"content": content}}]})
            finally:
                if request_id in response_channels:
                    del response_channels[request_id]
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


def run_server():
    logger.info("🚀 LMArenaBridge v2 Engine Starting...")
    uvicorn.run(app, host="0.0.0.0", port=5102)


@app.get("/health")
async def health():
    return JSONResponse(
        {
            "status": "ok",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "ws_connected": browser_ws is not None,
        }
    )


if __name__ == "__main__":
    run_server()
