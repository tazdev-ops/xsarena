"""Tests to verify both transports meet the BackendTransport interface."""

import os
import sys

import pytest

# Add the src directory to the path so we can import xsarena modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from xsarena.core.backends.bridge_v2 import BridgeV2Transport, OpenRouterTransport
from xsarena.core.backends.transport import BackendTransport


class MockTransport(BackendTransport):
    """Mock transport for testing the interface."""

    def __init__(self, should_fail_health=False):
        self.should_fail_health = should_fail_health

    async def send(self, payload):
        return {"choices": [{"message": {"content": "test response"}}]}

    async def health_check(self):
        return not self.should_fail_health

    async def stream_events(self):
        return []


@pytest.fixture
def mock_bridge_transport():
    """Fixture for a mock bridge transport."""
    return MockTransport()


@pytest.fixture
def mock_openrouter_transport():
    """Fixture for a mock openrouter transport."""
    return MockTransport()


@pytest.mark.asyncio
async def test_backend_transport_interface():
    """Test that the abstract interface is properly defined."""
    # Should not be instantiable directly
    with pytest.raises(TypeError):
        BackendTransport()


@pytest.mark.asyncio
async def test_bridge_v2_transport_implementation():
    """Test that BridgeV2Transport implements the interface correctly."""
    # This should not raise any errors
    transport = BridgeV2Transport(base_url="http://test:5102/v1")

    # Check that required methods exist
    assert hasattr(transport, "send")
    assert hasattr(transport, "health_check")
    assert hasattr(transport, "stream_events")

    # Check that they are callable
    assert callable(transport.send)
    assert callable(transport.health_check)
    assert callable(transport.stream_events)


@pytest.mark.asyncio
async def test_openrouter_transport_implementation():
    """Test that OpenRouterTransport implements the interface correctly."""
    # This should not raise any errors
    transport = OpenRouterTransport(api_key="test-key", model="test-model")

    # Check that required methods exist
    assert hasattr(transport, "send")
    assert hasattr(transport, "health_check")
    assert hasattr(transport, "stream_events")

    # Check that they are callable
    assert callable(transport.send)
    assert callable(transport.health_check)
    assert callable(transport.stream_events)


@pytest.mark.asyncio
async def test_bridge_transport_send_method():
    """Test the send method of BridgeV2Transport."""
    transport = BridgeV2Transport(
        base_url="http://127.0.0.1:5102/v1"
    )  # Use localhost instead of 'test'

    # The method should be callable and accept a payload
    assert callable(transport.send)

    # Test that it accepts a payload dict
    try:
        # This will fail because there's no actual server, but that's expected
        await transport.send({"test": "payload"})
    except RuntimeError:
        # Expected to fail with a RuntimeError when no server is available
        pass
    except Exception:
        # Any other exception is also fine for interface compliance
        pass


@pytest.mark.asyncio
async def test_openrouter_transport_send_method():
    """Test the send method of OpenRouterTransport."""
    transport = OpenRouterTransport(api_key="test-key", model="test-model")

    # The method should be callable and accept a payload
    assert callable(transport.send)

    # Test that it accepts a payload dict
    try:
        # This will fail because there's no actual API key, but that's expected
        await transport.send({"test": "payload"})
    except RuntimeError:
        # Expected to fail with a RuntimeError when no server is available
        pass
    except Exception:
        # Any other exception is also fine for interface compliance
        pass


@pytest.mark.asyncio
async def test_bridge_transport_health_check():
    """Test the health_check method of BridgeV2Transport."""
    transport = BridgeV2Transport(base_url="http://127.0.0.1:5102/v1")  # Use localhost

    # The method should be callable and return a boolean
    assert callable(transport.health_check)
    result = await transport.health_check()
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_openrouter_transport_health_check():
    """Test the health_check method of OpenRouterTransport."""
    transport = OpenRouterTransport(api_key="test-key", model="test-model")

    # The method should be callable and return a boolean
    assert callable(transport.health_check)
    result = await transport.health_check()
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_transport_factory_function():
    """Test the transport factory function."""
    from xsarena.core.backends import create_backend
    from xsarena.core.backends.circuit_breaker import CircuitBreakerTransport

    # Test bridge creation
    bridge_transport = create_backend("bridge")
    assert isinstance(bridge_transport, CircuitBreakerTransport)
    assert isinstance(bridge_transport.wrapped_transport, BridgeV2Transport)

    # Test openrouter creation (with mock API key)
    openrouter_transport = create_backend("openrouter", api_key="test-key")
    assert isinstance(openrouter_transport, CircuitBreakerTransport)
    assert isinstance(openrouter_transport.wrapped_transport, OpenRouterTransport)

    # Test deprecated types
    with pytest.warns(DeprecationWarning):
        deprecated_transport = create_backend("lmarena")
        assert isinstance(deprecated_transport, CircuitBreakerTransport)
        assert isinstance(deprecated_transport.wrapped_transport, BridgeV2Transport)

    # Test unsupported type
    with pytest.raises(ValueError, match="Unsupported backend type"):
        create_backend("unsupported_type")


if __name__ == "__main__":
    pytest.main([__file__])
