"""Backends package for XSArena."""
from typing import Dict, Any
from .transport import BackendTransport
from .bridge_v2 import BridgeV2Transport, OpenRouterTransport
import os
from dataclasses import dataclass


@dataclass
class Message:
    """A chat message."""
    role: str
    content: str


def create_backend(backend_type: str, **kwargs) -> BackendTransport:
    """Factory function to create the appropriate backend transport."""
    if backend_type == "bridge":
        return BridgeV2Transport(
            base_url=kwargs.get("base_url", "http://127.0.0.1:5102/v1")
        )
    elif backend_type in ("lmarena", "lmarena-ws"):
        # DEPRECATED: Use 'bridge' instead
        import warnings
        warnings.warn(f"Backend type '{backend_type}' is deprecated. Use 'bridge' instead.", DeprecationWarning)
        return BridgeV2Transport(
            base_url=kwargs.get("base_url", "http://127.0.0.1:5102/v1")
        )
    elif backend_type == "openrouter":
        api_key = kwargs.get("api_key") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OpenRouter API key not configured. Set OPENROUTER_API_KEY or pass api_key=...")
        return OpenRouterTransport(api_key=api_key, model=kwargs.get("model", "openai/gpt-4o"))
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")