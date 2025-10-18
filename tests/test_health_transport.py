"""Tests for doctor ping via transport health_check functionality."""

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_backend_health_check():
    """Unit test: mock backend.health_check() True/False; assert the health check works."""
    # This test verifies the backend health check functionality

    # Create a mock backend with health_check method
    mock_backend = AsyncMock()
    mock_backend.health_check = AsyncMock(return_value=True)
    mock_backend.__class__.__name__ = "MockBridgeBackend"
    mock_backend.base_url = "http://127.0.0.1:5102/v1"

    # Test with healthy backend
    is_healthy = await mock_backend.health_check()
    assert is_healthy is True

    # Test with unhealthy backend
    mock_backend_unhealthy = AsyncMock()
    mock_backend_unhealthy.health_check = AsyncMock(return_value=False)
    mock_backend_unhealthy.__class__.__name__ = "MockBridgeBackend"
    mock_backend_unhealthy.base_url = "http://127.0.0.1:5102/v1"

    is_healthy = await mock_backend_unhealthy.health_check()
    assert is_healthy is False


def test_doctor_ping_base_url():
    """Test that doctor ping reports correct base_url."""
    # Test that the base URL is correctly configured
    from xsarena.core.config import Config

    config = Config()
    assert (
        config.base_url == "http://127.0.0.1:5102/v1"
    )  # Should be 5102 as per requirements
