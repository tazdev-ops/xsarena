#!/usr/bin/env python3
"""
Simple ID updater server for XSArena.
This server receives ID updates from the userscript and updates the config.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CONFIG = {}


def load_config():
    global CONFIG
    # Load config from .xsarena/config.yml
    try:
        import yaml

        yaml_config_path = Path(".xsarena/config.yml")
        if yaml_config_path.exists():
            with open(yaml_config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f) or {}
            # Extract bridge config if present
            CONFIG = yaml_config.get("bridge", {})
            logger.info(f"Successfully loaded configuration from '{yaml_config_path}'.")
        else:
            logger.error(
                ".xsarena/config.yml not found. Please run 'xsarena project config-migrate'"
            )
            CONFIG = {}
    except Exception as e:
        logger.error(
            f"Failed to load configuration: {e}. Please run 'xsarena project config-migrate'"
        )
        CONFIG = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_config()
    logger.info("ID Updater server startup complete.")
    yield
    logger.info("ID Updater server shutting down.")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _update_ids(request: Request):
    """Internal function to update session and message IDs."""
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


@app.post("/internal/id_capture/update")
async def update_id_capture_legacy(request: Request):
    """Update session and message IDs from the userscript (legacy endpoint)."""
    return await _update_ids(request)


@app.post("/update")
async def update_id_capture(request: Request):
    """Update session and message IDs from the userscript (new endpoint)."""
    return await _update_ids(request)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "session_id": CONFIG.get("session_id"),
        "message_id": CONFIG.get("message_id"),
    }


if __name__ == "__main__":
    import os

    api_port = int(os.getenv("PORT", "5103"))  # Default to port 5103 to avoid conflicts
    logger.info(f"🚀 XSArena ID Updater server starting on port {api_port}...")
    uvicorn.run(app, host="0.0.0.0", port=api_port)
