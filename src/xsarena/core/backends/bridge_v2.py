"""Bridge transport implementation for XSArena backends."""

import asyncio
import os
from typing import Any, Dict, List

import aiohttp

from .transport import BackendTransport, BaseEvent


class BridgeV2Transport(BackendTransport):
    """Transport that communicates with the local bridge server."""

    def __init__(self, base_url: str = "http://127.0.0.1:5102/v1", timeout: int = 60):
        self.base_url = os.getenv("XSA_BRIDGE_URL", base_url)
        self.timeout = timeout

    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a payload to the bridge server and return the response."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # The payload should already be in the correct format for the bridge
            for attempt in range(2):
                try:
                    async with session.post(
                        f"{self.base_url}/chat/completions", json=payload
                    ) as resp:
                        if resp.status >= 500 and attempt == 0:
                            await asyncio.sleep(0.5)
                            continue
                        if resp.status != 200:
                            text = (await resp.text())[:300]
                            raise RuntimeError(f"Bridge error {resp.status}: {text}")
                        result = await resp.json()
                        return result
                except aiohttp.ClientError:
                    if attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                    raise

    async def health_check(self) -> bool:
        """Check if the bridge server is healthy and responsive."""
        try:
            async with aiohttp.ClientSession() as session, session.get(
                f"{self.base_url.replace('/v1', '')}/health"
            ) as resp:
                if resp.status == 200:
                    health_data = await resp.json()
                    return health_data.get("ws_connected", False) is True
                return False
        except:
            return False

    async def stream_events(self) -> List[BaseEvent]:
        """Stream events from the backend."""
        # For the bridge, we might poll for status updates
        # This is a placeholder implementation
        return []


# For backward compatibility with the old interface
class OpenRouterTransport(BackendTransport):
    """Transport that communicates directly with OpenRouter."""

    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

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

        for attempt in range(2):
            try:
                async with aiohttp.ClientSession() as session, session.post(
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
            async with aiohttp.ClientSession() as session, session.get(
                f"{self.base_url}/models", headers=headers
            ) as response:
                return response.status == 200
        except:
            return False

    async def stream_events(self) -> List[BaseEvent]:
        """Stream events from the backend."""
        # OpenRouter doesn't support event streaming in the same way
        # This is a placeholder implementation
        return []
