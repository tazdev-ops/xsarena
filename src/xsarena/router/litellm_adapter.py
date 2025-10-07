"""LiteLLM adapter for XSArena - provides model routing capabilities."""

import os
from typing import Dict, List, Optional

import aiohttp


class LiteLLMAdapter:
    """Thin wrapper for LiteLLM API calls with fallback chain support."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the LiteLLM adapter.

        Args:
            base_url: LiteLLM base URL (defaults to LITELLM_BASE env var)
            api_key: API key (defaults to LITELLM_API_KEY env var)
        """
        self.base_url = base_url or os.getenv("LITELLM_BASE")
        self.api_key = api_key or os.getenv("LITELLM_API_KEY")

    def is_configured(self) -> bool:
        """Check if the adapter is properly configured."""
        return bool(self.base_url and self.api_key)

    async def call(self, messages: List[Dict[str, str]], model: str, stream: bool = False, **kwargs) -> str:
        """
        Make a call to LiteLLM API.

        Args:
            messages: List of message dicts with role and content
            model: Model identifier to use
            stream: Whether to stream the response (currently ignored)
            **kwargs: Additional parameters to pass to the API

        Returns:
            Generated text response

        Raises:
            RuntimeError: If LiteLLM is not configured
            aiohttp.ClientError: If API call fails
        """
        if not self.is_configured():
            raise RuntimeError("LiteLLM not configured - set LITELLM_BASE and LITELLM_API_KEY")

        url = f"{self.base_url}/v1/chat/completions"

        payload = {"model": model, "messages": messages, "stream": stream, **kwargs}

        # Add any additional parameters
        if "temperature" not in payload:
            payload["temperature"] = 0.7
        if "max_tokens" not in payload:
            payload["max_tokens"] = 2048

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise aiohttp.ClientError(f"LiteLLM API error {resp.status}: {text}")

                response_data = await resp.json()

                # Extract the content from the response
                choices = response_data.get("choices", [])
                if not choices:
                    raise ValueError("No choices returned from LiteLLM API")

                content = choices[0].get("message", {}).get("content", "")
                return content


# Fallback chain for model routing
FALLBACK_CHAIN = ["openrouter/auto", "anthropic/claude-3-sonnet", "openai/gpt-4o-mini", "openai/gpt-3.5-turbo"]


def get_router_backend() -> Optional[str]:
    """Get the configured router backend from environment variables."""
    return os.getenv("XSA_ROUTER_BACKEND", "openrouter")  # Default to openrouter


def get_fallback_chain() -> List[str]:
    """Get the model fallback chain from project config or defaults."""
    # This would typically be loaded from project config
    return FALLBACK_CHAIN
