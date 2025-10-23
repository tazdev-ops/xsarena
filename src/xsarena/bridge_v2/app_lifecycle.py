"""Application lifecycle management for bridge v2."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .handlers import CONFIG
from .websocket import start_idle_restart_thread, stop_idle_restart_thread

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup logic
    logger.info("Bridge v2 starting up")
    # Start idle restart thread on startup
    start_idle_restart_thread(CONFIG)

    yield  # Application runs here

    # Shutdown logic
    logger.info("Bridge v2 shutting down")
    # Stop idle restart thread on shutdown
    stop_idle_restart_thread()


def setup_idle_restart():
    """Setup for idle restart functionality."""
    # Implementation will depend on existing idle restart logic
    pass
