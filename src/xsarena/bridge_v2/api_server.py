# src/xsarena/bridge_v2/api_server.py
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import job_service as job_service_module

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import from new modules
from .handlers import (
    CONFIG,
    MODEL_NAME_TO_ID_MAP,
    MODEL_ENDPOINT_MAP,
    _internal_ok,
    chat_completions_handler,
    format_openai_chunk,
    format_openai_finish_chunk,
    load_config,
    load_model_endpoint_map,
    load_model_map,
    update_available_models_handler,
    update_id_capture_handler,
)
from .websocket import (
    REFRESHING_BY_REQUEST,
    browser_ws,
    cloudflare_verified,
    response_channels,
    start_idle_restart_thread,
    stop_idle_restart_thread,
    websocket_endpoint,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    load_model_map()
    load_model_endpoint_map()
    start_idle_restart_thread(CONFIG)  # Start idle restart thread with CONFIG
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
async def websocket_endpoint_wrapper(websocket: WebSocket):
    """Wrapper for the websocket endpoint to pass CONFIG."""
    return await websocket_endpoint(websocket, CONFIG)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    global last_activity_time
    # Update last activity time
    last_activity_time = datetime.now()

    # Call the handler from the handlers module
    return await chat_completions_handler(
        request,
        browser_ws,
        response_channels,
        REFRESHING_BY_REQUEST,
        cloudflare_verified,
    )


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
    # Call the handler from the handlers module
    return await update_available_models_handler(request)


@app.post("/internal/id_capture/update")
async def update_id_capture(request: Request):
    if not _internal_ok(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Call the handler from the handlers module
    return await update_id_capture_handler(request)


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
        for model_name in MODEL_NAME_TO_ID_MAP:  # Iterate over keys
            # Try to determine if it's an image model
            try:
                with open("models.json", "r", encoding="utf-8") as f:
                    models_data = json.load(f)
                model_info = models_data.get(model_name)
                if model_info and isinstance(model_info, dict):
                    if model_info.get("type") == "image":
                        pass
            except (FileNotFoundError, json.JSONDecodeError):
                pass  # If models.json doesn't exist, continue with is_image format

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


# API endpoints for jobs
@app.get("/api/jobs")
async def api_list_jobs():
    """API endpoint to list all jobs."""
    job_service_instance = job_service_module.JobService()
    jobs = job_service_instance.list_jobs()

    return {"jobs": jobs}


@app.get("/api/jobs/{job_id}")
async def api_get_job(job_id: str):
    """API endpoint to get a specific job's status."""
    job_service_instance = job_service_module.JobService()
    job_data = job_service_instance.get_job(job_id)

    if job_data is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_data


# Health endpoint expected by XSArena
@app.get("/health")
def health():
    global last_activity_time
    try:
        # Try to get last_activity_time, default to None if not defined yet
        last_activity_iso = (
            last_activity_time.isoformat()
            if "last_activity_time" in globals() and last_activity_time
            else None
        )
    except (AttributeError, NameError):
        last_activity_iso = None

    return {
        "status": "ok",
        "ts": datetime.now().isoformat(),
        "ws_connected": browser_ws is not None,
        "last_activity": last_activity_iso,
        "version": CONFIG.get("version", "unknown"),
    }


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


def format_openai_chunk(content, model, request_id):
    """Format content as an OpenAI-compatible chunk for streaming."""
    import json
    import time

    chunk = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def format_openai_finish_chunk(model, request_id, reason="stop"):
    """Format a finish chunk for OpenAI-compatible streaming."""
    import json
    import time

    chunk = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": reason}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


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
