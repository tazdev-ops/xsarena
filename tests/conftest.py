import pytest
from unittest.mock import patch, AsyncMock
from xsarena.core.backends import Backend, Message
from typing import List


class FakeBackend(Backend):
    """Fake backend for testing that returns deterministic content."""
    
    def __init__(self, response_content: str = "Test response content", next_marker: str = None):
        self.response_content = response_content
        self.next_marker = next_marker
        self.call_count = 0
        self.sent_messages = []
    
    async def send(self, messages: List[Message], stream: bool = False) -> str:
        """Return deterministic content, including NEXT markers if specified."""
        self.call_count += 1
        self.sent_messages.extend(messages)
        
        if self.next_marker and self.call_count > 1:  # Add NEXT marker after first response
            return f"{self.response_content}\n\nNEXT: [{self.next_marker}]"
        return self.response_content


@pytest.fixture
def fake_backend():
    """Fixture that provides a FakeBackend instance."""
    return FakeBackend(response_content="Test response", next_marker="END")


@pytest.fixture
def patch_create_backend():
    """Fixture that patches create_backend to return FakeBackend."""
    from xsarena.core.backends import create_backend
    
    def _patch_create_backend(backend_type: str = "bridge", **kwargs):
        return FakeBackend(response_content="Test response", next_marker="END")
    
    with patch('xsarena.core.backends.create_backend', side_effect=_patch_create_backend) as mock:
        yield mock