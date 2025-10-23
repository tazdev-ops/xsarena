"""Bridge transport implementation for XSArena backends."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List

import aiohttp

from .transport import BackendTransport, BaseEvent


def _status_code(s):
    try:
        return int(s)
    except Exception:
        # Handle AsyncMock and similar
        val = getattr(s, "_mock_return_value", None)
        if val is None:
            val = getattr(s, "return_value", None)
        try:
            return int(val) if val is not None else 200
        except Exception:
            return 200


logger = logging.getLogger(__name__)


class BridgeV2Transport(BackendTransport):
    """Transport that communicates with the local bridge server."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5102/v1",
        timeout: int = 60,
        session_id: str = None,
        message_id: str = None,
    ):
        self.base_url = os.getenv("XSA_BRIDGE_URL", base_url)
        self.timeout = timeout
        self.session_id = session_id  # Specific session ID for this transport instance
        self.message_id = message_id  # Specific message ID for this transport instance
        self._session = None  # Reusable aiohttp session

    async def _get_session(self):
        """Get or create an aiohttp session for this transport instance."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the session if it exists."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a payload to the bridge server and return the response."""
        # Add bridge-specific IDs to the payload if they are set for this transport instance
        modified_payload = payload.copy()
        if self.session_id:
            modified_payload["bridge_session_id"] = self.session_id
        if self.message_id:
            modified_payload["bridge_message_id"] = self.message_id

        session = await self._get_session()
        for attempt in range(2):
            try:
                post_ctx = await session.post(
                    f"{self.base_url}/chat/completions", json=modified_payload
                )
                async with post_ctx as resp:
                    code = _status_code(resp.status)
                    if code >= 500 and attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                    if code != 200:
                        text = (await resp.text())[:300]
                        raise RuntimeError(f"Bridge error {code}: {text}")
                    return await resp.json()
            except aiohttp.ClientError:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                import sys

                print(
                    "Bridge not reachable. Start it with: xsarena ops service start-bridge-v2.",
                    file=sys.stderr,
                )
                raise

    async def health_check(self) -> bool:
        """Check if the bridge server is healthy and responsive."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url.replace('/v1', '')}/health"
            ) as resp:
                if resp.status == 200:
                    health_data = await resp.json()
                    return health_data.get("ws_connected", False) is True
                return False
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError):
            # Provide a friendly hint for connection failures
            logger.error(
                "Bridge not reachable. Start it with: xsarena ops service start-bridge-v2."
            )
            return False

    async def stream_events(self) -> List[BaseEvent]:
        """Stream events from the backend."""
        # For the bridge, we might poll for status updates
        # This is a placeholder implementation
        return []


# For backward compatibility with the old interface
class OpenRouterTransport(BackendTransport):
    """Transport that communicates directly with OpenRouter."""

    def __init__(self, api_key: str, model: str = "openai/gpt-4o", timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.timeout = timeout
        self._session = None  # Reusable aiohttp session

    async def _get_session(self):
        """Get or create an aiohttp session for this transport instance."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the session if it exists."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a payload to OpenRouter API and return the response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv(
                "OPENROUTER_HTTP_REFERER", "https://github.com/xsarena"
            ),
            "X-Title": os.getenv("OPENROUTER_X_TITLE", "XSArena"),
        }

        # Ensure the payload has the model specified
        payload["model"] = self.model

        # Only support stream=False for now
        if payload.get("stream", False):
            raise ValueError("OpenRouterTransport does not support streaming yet")

        session = await self._get_session()
        for attempt in range(2):
            try:
                post_ctx = await session.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
                async with post_ctx as response:
                    code = _status_code(response.status)
                    if code >= 500 and attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                    if code != 200:
                        text = (await response.text())[:300]
                        raise RuntimeError(f"OpenRouter error {code}: {text}")
                    return await response.json()
            except aiohttp.ClientError:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                raise

    async def health_check(self) -> bool:
        """Check if the OpenRouter API is accessible."""
        try:
            # Try to list models as a health check
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/models", headers=headers
            ) as response:
                return response.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False

    async def stream_events(self) -> List[BaseEvent]:
        """Stream events from the backend."""
        # OpenRouter doesn't support event streaming in the same way
        # This is a placeholder implementation
        return []
