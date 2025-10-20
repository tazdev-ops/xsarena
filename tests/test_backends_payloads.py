"""Tests for backend payload construction and error handling."""


from unittest.mock import patch

import pytest
from xsarena.core.backends.bridge_v2 import BridgeV2Transport, OpenRouterTransport


@pytest.mark.asyncio
async def test_bridge_backend_payload():
    """Test BridgeV2Transport payload construction."""
    from unittest.mock import AsyncMock

    transport = BridgeV2Transport(base_url="http://test:8080/v1")

    payload = {
        "messages": [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "User message"},
        ]
    }

    # Create the response mock
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Response"}}]
    }

    # Mock the entire session.post call to return the response directly
    with patch("aiohttp.ClientSession") as MockClientSession:
        # Create a session mock that returns our post context manager
        session_instance = AsyncMock()
        session_instance.post.return_value.__aenter__.return_value = mock_response
        MockClientSession.return_value.__aenter__.return_value = session_instance

        await transport.send(payload)

        # Verify the call was made correctly
        session_instance.post.assert_called_once()
        call_args = session_instance.post.call_args
        assert call_args[0][0] == "http://test:8080/v1/chat/completions"

        sent_payload = call_args[1]["json"]
        assert "messages" in sent_payload
        assert len(sent_payload["messages"]) == 2
        assert sent_payload["messages"][0]["role"] == "system"
        assert sent_payload["messages"][0]["content"] == "System message"
        assert sent_payload["messages"][1]["role"] == "user"
        assert sent_payload["messages"][1]["content"] == "User message"


@pytest.mark.asyncio
async def test_bridge_backend_error_handling():
    """Test BridgeV2Transport error handling."""
    from unittest.mock import AsyncMock

    import aiohttp

    transport = BridgeV2Transport(base_url="http://test:8080/v1")

    payload = {"messages": [{"role": "user", "content": "Test message"}]}

    # Create the response mock for error case
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"

    # Mock the entire session.post call to return the error response directly
    with patch.object(aiohttp.ClientSession, "post", autospec=True) as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await transport.send(payload)

        assert "Bridge error 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openrouter_backend_payload():
    """Test OpenRouterTransport payload construction."""
    from unittest.mock import AsyncMock

    transport = OpenRouterTransport(api_key="test-key", model="test-model")

    payload = {"messages": [{"role": "user", "content": "User message"}]}

    # Create the response mock
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Response"}}]
    }

    # Mock the entire session.post call to return the response directly
    with patch("aiohttp.ClientSession") as MockClientSession:
        # Create a session mock that returns our post context manager
        session_instance = AsyncMock()
        session_instance.post.return_value.__aenter__.return_value = mock_response
        MockClientSession.return_value.__aenter__.return_value = session_instance

        await transport.send(payload)

        # Verify the payload structure
        session_instance.post.assert_called_once()
        call_args = session_instance.post.call_args

        # Check URL
        assert call_args[0][0] == "https://openrouter.ai/api/v1/chat/completions"

        # Check headers
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"

        # Check payload
        sent_payload = call_args[1]["json"]
        assert sent_payload["model"] == "test-model"
        assert len(sent_payload["messages"]) == 1
        assert sent_payload["messages"][0]["role"] == "user"
        assert sent_payload["messages"][0]["content"] == "User message"


@pytest.mark.asyncio
async def test_openrouter_backend_stream_not_supported():
    """Test OpenRouterTransport stream not supported error."""
    transport = OpenRouterTransport(api_key="test-key", model="test-model")

    payload = {
        "messages": [{"role": "user", "content": "Test message"}],
        "stream": True,
    }

    with pytest.raises(ValueError) as exc_info:
        await transport.send(payload)

    assert "does not support streaming" in str(exc_info.value)
