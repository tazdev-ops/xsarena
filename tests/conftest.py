from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from xsarena.core.backends.transport import BackendTransport


class FakeBackend(BackendTransport):
    """Fake backend for testing that returns deterministic content."""

    def __init__(
        self, response_content: str = "Test response content", next_marker: str = None
    ):
        self.response_content = response_content
        self.next_marker = next_marker
        self.call_count = 0
        self.sent_messages = []

    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Return deterministic content, including NEXT markers if specified."""
        self.call_count += 1
        # Extract messages from payload for tracking
        messages = payload.get("messages", [])
        self.sent_messages.extend(messages)

        if (
            self.next_marker and self.call_count > 1
        ):  # Add NEXT marker after first response
            return {
                "choices": [
                    {
                        "message": {
                            "content": f"{self.response_content}\n\nNEXT: [{self.next_marker}]"
                        }
                    }
                ]
            }
        return {"choices": [{"message": {"content": self.response_content}}]}

    async def health_check(self) -> bool:
        """Health check for the fake backend."""
        return True

    async def stream_events(self) -> List[Any]:
        """Stream events for the fake backend."""
        return []


@pytest.fixture
def fake_backend():
    """Fixture that provides a FakeBackend instance."""
    return FakeBackend(response_content="Test response", next_marker="END")


@pytest.fixture
def patch_create_backend():
    """Fixture that patches create_backend to return FakeBackend."""

    def _patch_create_backend(backend_type: str = "bridge", **kwargs):
        return FakeBackend(response_content="Test response", next_marker="END")

    with patch(
        "xsarena.core.backends.create_backend", side_effect=_patch_create_backend
    ) as mock:
        yield mock
