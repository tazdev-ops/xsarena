"""Backends package for XSArena."""

import os
from dataclasses import dataclass

from .bridge_v2 import BridgeV2Transport, OpenRouterTransport
from .circuit_breaker import CircuitBreakerTransport
from .transport import BackendTransport


@dataclass
class Message:
    """A chat message."""

    role: str
    content: str


class NullTransport(BackendTransport):
    """Offline shim backend for tests/demos."""

    def __init__(self, script: list = None):
        self._calls = 0
        self._script = script or [
            "Offline sample. NEXT: [Continue]",
            "Offline final. NEXT: [END]",
        ]

    async def send(self, payload: dict) -> dict:
        self._calls += 1
        if self._calls <= len(self._script):
            content = self._script[self._calls - 1]
        else:
            # If we've exhausted the script, return a default response
            content = f"Offline continuation {self._calls}. NEXT: [END]"
        return {"choices": [{"message": {"content": content}}]}

    async def health_check(self) -> bool:
        return True

    async def stream_events(self) -> list:
        return []


def create_backend(backend_type: str, **kwargs) -> BackendTransport:
    """Factory function to create the appropriate backend transport."""
    # Create the base transport
    if backend_type in ("null", "offline"):
        base_transport = NullTransport(script=kwargs.get("script"))
    elif backend_type == "bridge":
        base_transport = BridgeV2Transport(
            base_url=kwargs.get("base_url", "http://127.0.0.1:5102/v1"),
            session_id=kwargs.get("session_id"),
            message_id=kwargs.get("message_id"),
        )
    elif backend_type in ("lmarena", "lmarena-ws"):
        # DEPRECATED: Use 'bridge' instead
        import warnings

        warnings.warn(
            f"Backend type '{backend_type}' is deprecated. Use 'bridge' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        base_transport = BridgeV2Transport(
            base_url=kwargs.get("base_url", "http://127.0.0.1:5102/v1")
        )
    elif backend_type == "openrouter":
        api_key = kwargs.get("api_key") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenRouter API key not configured. Set OPENROUTER_API_KEY or pass api_key=..."
            )
        base_transport = OpenRouterTransport(
            api_key=api_key, model=kwargs.get("model", "openai/gpt-4o")
        )
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")

    # Wrap with circuit breaker
    return CircuitBreakerTransport(
        wrapped_transport=base_transport,
        failure_threshold=kwargs.get("circuit_breaker_threshold", 5),
        recovery_timeout=kwargs.get("circuit_breaker_timeout", 30),
        failure_ratio=kwargs.get("circuit_breaker_ratio", 0.5),
    )
