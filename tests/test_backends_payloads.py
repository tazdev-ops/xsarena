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
    mock_response.close = AsyncMock()  # Add close method for the response

    # Create a proper mock session that will be returned by ClientSession()
    mock_session = AsyncMock()
    mock_post_context = AsyncMock()
    mock_post_context.__aenter__.return_value = mock_response
    mock_session.post.return_value = mock_post_context

    with patch(
        "aiohttp.ClientSession", return_value=mock_session
    ) as mock_session_constructor:
        await transport.send(payload)

        # Verify the session was created
        mock_session_constructor.assert_called_once()

        # Verify the call was made correctly
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
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

    transport = BridgeV2Transport(base_url="http://test:8080/v1")

    payload = {"messages": [{"role": "user", "content": "Test message"}]}

    # Create the response mock for error case
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_response.close = AsyncMock()  # Add close method for the response

    # Create a mock session
    mock_session = AsyncMock()
    mock_post_context = AsyncMock()
    mock_post_context.__aenter__.return_value = mock_response
    mock_session.post.return_value = mock_post_context

    # Mock the entire session creation
    with patch("aiohttp.ClientSession", return_value=mock_session):
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
    mock_response.close = AsyncMock()  # Add close method for the response

    # Mock the session and its post method properly
    mock_session = AsyncMock()
    mock_post_context = AsyncMock()
    mock_post_context.__aenter__.return_value = mock_response
    mock_session.post.return_value = mock_post_context

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await transport.send(payload)

        # Verify the payload structure
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args

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
