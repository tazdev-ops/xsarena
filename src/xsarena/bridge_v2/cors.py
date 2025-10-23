"""CORS configuration for bridge v2."""

import logging
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def setup_cors(app: FastAPI, cors_origins: Optional[List[str]] = None):
    """Setup CORS middleware for the application."""
    if cors_origins is None:
        # Use CONFIG.cors_origins or default to "*" as mentioned in the spec
        cors_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(f"CORS configured with origins: {cors_origins}")
