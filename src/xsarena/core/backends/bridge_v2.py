"""Bridge transport implementation for XSArena backends."""

import asyncio
import json
import os
from typing import Any, Dict, List

import aiohttp

from .transport import BackendTransport, BaseEvent


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

    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a payload to the bridge server and return the response."""
        # Add bridge-specific IDs to the payload if they are set for this transport instance
        modified_payload = payload.copy()
        if self.session_id:
            modified_payload["bridge_session_id"] = self.session_id
        if self.message_id:
            modified_payload["bridge_message_id"] = self.message_id

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(2):
                try:
                    async with session.post(
                        f"{self.base_url}/chat/completions", json=modified_payload
                    ) as resp:
                        if resp.status >= 500 and attempt == 0:
                            await asyncio.sleep(0.5)
                            continue
                        if resp.status != 200:
                            text = (await resp.text())[:300]
                            raise RuntimeError(f"Bridge error {resp.status}: {text}")
                        result = await resp.json()
                        return result
                except aiohttp.ClientError as e:
                    if attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                    # Provide a friendly hint for connection failures
                    import sys

                    print(
                        "Bridge not reachable. Start it with: xsarena ops service start-bridge-v2.",
                        file=sys.stderr,
                    )
                    raise e

    async def health_check(self) -> bool:
        """Check if the bridge server is healthy and responsive."""
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.base_url.replace('/v1', '')}/health"
                ) as resp:
                    if resp.status == 200:
                        health_data = await resp.json()
                        return health_data.get("ws_connected", False) is True
                    return False
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError):
            # Provide a friendly hint for connection failures
            import sys

            print(
                "Bridge not reachable. Start it with: xsarena ops service start-bridge-v2.",
                file=sys.stderr,
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

        timeout = aiohttp.ClientTimeout(
            total=self.timeout if hasattr(self, "timeout") else 60
        )
        for attempt in range(2):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status >= 500 and attempt == 0:
                            await asyncio.sleep(0.5)
                            continue
                        if response.status != 200:
                            text = (await response.text())[:300]
                            raise RuntimeError(
                                f"OpenRouter error {response.status}: {text}"
                            )
                        result = await response.json()
                        return result
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
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
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
