"""Guard utilities for bridge v2 (auth check, rate limiter, busy checks)."""

import logging
import time

from fastapi import Request

logger = logging.getLogger(__name__)

# Global state for rate limiting and server status
_rate_limits = {}  # Store rate limit info per peer
_server_busy = False  # Track if server is busy


def check_auth(request: Request) -> bool:
    """Check authentication for the request."""
    # Check if API key is required
    from .config_loaders import CONFIG

    required_api_key = CONFIG.get("api_key")

    if required_api_key:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="Missing Bearer token")

        provided_api_key = auth_header[7:]  # Remove "Bearer " prefix
        if provided_api_key != required_api_key:
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="Invalid API key")

    return True


def check_rate_limit(request: Request) -> bool:
    """Check rate limits for the request."""
    # Get peer identifier (could be IP, API key, etc.)
    peer_id = request.client.host if request.client else "unknown"

    # Get rate limit settings from config
    from .config_loaders import CONFIG

    burst = int(CONFIG.get("rate_limit_burst", 10))
    window = int(CONFIG.get("rate_limit_window", 60))

    current_time = time.time()

    # Initialize peer data if not exists
    if peer_id not in _rate_limits:
        _rate_limits[peer_id] = []

    # Remove requests older than the window
    _rate_limits[peer_id] = [
        req_time
        for req_time in _rate_limits[peer_id]
        if current_time - req_time < window
    ]

    # Check if limit exceeded
    if len(_rate_limits[peer_id]) >= burst:
        from fastapi import HTTPException

        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Add current request
    _rate_limits[peer_id].append(current_time)

    return True


def check_server_busy() -> bool:
    """Check if the server is busy."""
    global _server_busy
    if _server_busy:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Server busy")
    return True


def _internal_ok(request: Request) -> bool:
    """Check if internal request is authorized."""
    from .config_loaders import CONFIG

    expected_token = CONFIG.get("internal_api_token", "dev-token-change-me")

    provided_token = request.headers.get("x-internal-token") or request.headers.get(
        "authorization", ""
    ).replace("Bearer ", "")

    if provided_token != expected_token:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Unauthorized internal access")

    return True
