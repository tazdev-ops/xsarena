"""Tests for backend payload construction and error handling."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from xsarena.core.backends import BridgeBackend, OpenRouterBackend, Message


@pytest.mark.asyncio
async def test_bridge_backend_payload():
    """Test BridgeBackend payload construction."""
    backend = BridgeBackend(base_url="http://test:8080/v1")
    
    messages = [
        Message(role="system", content="System message"),
        Message(role="user", content="User message")
    ]
    
    # Mock the aiohttp session
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        mock_post = AsyncMock()
        mock_post.__aenter__.return_value.__aexit__.return_value = None
        mock_session.post.return_value.__aenter__.return_value = mock_post
        
        mock_post.status = 200
        mock_post.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        
        result = await backend.send(messages)
        
        # Verify the payload structure
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "http://test:8080/v1/chat/completions"
        
        payload = call_args[1]["json"]
        assert "messages" in payload
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "System message"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == "User message"


@pytest.mark.asyncio
async def test_bridge_backend_error_handling():
    """Test BridgeBackend error handling."""
    backend = BridgeBackend(base_url="http://test:8080/v1")
    
    messages = [Message(role="user", content="Test message")]
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        mock_post = AsyncMock()
        mock_post.__aenter__.return_value.__aexit__.return_value = None
        mock_session.post.return_value.__aenter__.return_value = mock_post
        
        mock_post.status = 500
        mock_post.text.return_value = "Internal Server Error"
        
        with pytest.raises(RuntimeError) as exc_info:
            await backend.send(messages)
        
        assert "Bridge error 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openrouter_backend_payload():
    """Test OpenRouterBackend payload construction."""
    backend = OpenRouterBackend(api_key="test-key", model="test-model")
    
    messages = [
        Message(role="user", content="User message")
    ]
    
    # Mock the aiohttp session
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        mock_context = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_context
        
        mock_context.status = 200
        mock_context.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        
        result = await backend.send(messages)
        
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
        payload = call_args[1]["json"]
        assert payload["model"] == "test-model"
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "User message"


@pytest.mark.asyncio
async def test_openrouter_backend_stream_not_supported():
    """Test OpenRouterBackend stream not supported error."""
    backend = OpenRouterBackend(api_key="test-key", model="test-model")
    
    messages = [Message(role="user", content="Test message")]
    
    with pytest.raises(ValueError) as exc_info:
        await backend.send(messages, stream=True)
    
    assert "does not support streaming" in str(exc_info.value)