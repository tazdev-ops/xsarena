"""Backend implementations for XSArena."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

import aiohttp
import os
import asyncio


@dataclass
class Message:
    """A chat message."""

    role: str
    content: str


class Backend(ABC):
    """Abstract base class for backends."""

    @abstractmethod
    async def send(self, messages: List[Message], stream: bool = False) -> str:
        """Send messages to the backend and return the response."""
        pass


class BridgeBackend(Backend):
    """Backend that communicates with the local bridge server."""

    def __init__(self, base_url: str = "http://127.0.0.1:5102/v1", timeout: int = 60):
        self.base_url = os.getenv("XSA_BRIDGE_URL", base_url)
        self.session_id = None
        self.timeout = timeout

    async def send(self, messages: List[Message], stream: bool = False) -> str:
        """Send messages to the bridge server."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # First, we need to push the messages to the server
            data = {
                "messages": [
                    {"role": msg.role, "content": msg.content} for msg in messages
                ],
                "stream": stream,
            }

            # Wait for response from the bridge (this would use the polling mechanism)
            # In the actual implementation, this would interact with your CSP-safe polling system
            for attempt in range(2):
                try:
                    async with session.post(f"{self.base_url}/chat/completions", json=data) as resp:
                        if resp.status >= 500 and attempt == 0:
                            await asyncio.sleep(0.5)
                            continue
                        if resp.status != 200:
                            text = (await resp.text())[:300]
                            raise RuntimeError(f"Bridge error {resp.status}: {text}")
                        result = await resp.json()
                        return result.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
                except aiohttp.ClientError as e:
                    if attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                    raise


class OpenRouterBackend(Backend):
    """Backend that communicates directly with OpenRouter."""

    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    async def send(self, messages: List[Message], stream: bool = False) -> str:
        """Send messages to OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://github.com/xsarena"),
            "X-Title": os.getenv("OPENROUTER_X_TITLE", "XSArena"),
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": msg.role, "content": msg.content} for msg in messages
            ],
            "stream": stream,
        }

        # Only support stream=False for now
        if stream:
            raise ValueError("OpenRouterBackend does not support streaming yet")
        
        for attempt in range(2):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions", headers=headers, json=data
                    ) as response:
                        if response.status >= 500 and attempt == 0:
                            await asyncio.sleep(0.5)
                            continue
                        if response.status != 200:
                            text = (await response.text())[:300]
                            raise RuntimeError(f"OpenRouter error {response.status}: {text}")
                        result = await response.json()
                        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            except aiohttp.ClientError as e:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                raise

    def estimate_cost(self, messages: List[Message]) -> Dict[str, float]:
        """Estimate the token usage and cost."""
        # Rough estimation based on character count
        total_chars = sum(len(msg.content) for msg in messages)
        input_tokens = total_chars // 4  # Rough estimate: 1 token ~ 4 chars
        output_tokens = 2048  # Estimated max response tokens

        # Pricing example (would need to be updated with actual OpenRouter prices)
        input_cost_per_token = 0.00001  # Example: $0.01 per 1K input tokens
        output_cost_per_token = 0.00003  # Example: $0.03 per 1K output tokens

        estimated_cost = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": (input_tokens * input_cost_per_token)
            + (output_tokens * output_cost_per_token),
        }

        return estimated_cost


# Backend factory
def create_backend(backend_type: str, **kwargs) -> Backend:
    """Factory function to create the appropriate backend."""
    if backend_type == "bridge":
        return BridgeBackend(
            base_url=kwargs.get("base_url", "http://127.0.0.1:5102/v1")
        )
    elif backend_type in ("lmarena", "lmarena-ws"):
        # Use your WS bridge’s OpenAI-compatible API
        return BridgeBackend(
            base_url=kwargs.get("base_url", "http://127.0.0.1:5102/v1")
        )
    elif backend_type == "openrouter":
        api_key = kwargs.get("api_key") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OpenRouter API key not configured. Set OPENROUTER_API_KEY or pass api_key=...")
        return OpenRouterBackend(api_key=api_key, model=kwargs.get("model", "openai/gpt-4o"))
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")
