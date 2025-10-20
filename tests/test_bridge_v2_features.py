"""Unit tests for bridge v2 features."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

# Add the bridge_v2 module to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import the app from bridge_v2.api_server
from xsarena.bridge_v2.api_server import app, convert_openai_to_lmarena_payload

client = TestClient(app)


def test_bridge_role_normalization():
    """Test developer→system role normalization."""
    # Test data with developer role
    openai_data = {
        "messages": [
            {"role": "developer", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ]
    }

    # Mock config
    with (
        patch(
            "xsarena.bridge_v2.api_server.CONFIG",
            {"tavern_mode_enabled": False, "bypass_enabled": False},
        ),
        patch(
            "xsarena.bridge_v2.api_server.MODEL_NAME_TO_ID_MAP",
            {"test-model": "test-id"},
        ),
    ):
        result = asyncio.run(
            convert_openai_to_lmarena_payload(
                openai_data, 
                "session123", 
                "msg123", 
                "test-model",
                {"test-model": "test-id"},  # model_name_to_id_map
                {},  # model_endpoint_map
                {"tavern_mode_enabled": False, "bypass_enabled": False}  # config
            )
        )

    # Check that developer role was converted to system
    message_templates = result["message_templates"]
    assert message_templates[0]["role"] == "system"
    assert message_templates[0]["content"] == "You are a helpful assistant"
    assert message_templates[1]["role"] == "user"
    assert message_templates[1]["content"] == "Hello"


def test_bridge_tavern_merge():
    """Test multiple system prompts merge in tavern mode."""
    # Test data with multiple system messages
    openai_data = {
        "messages": [
            {"role": "system", "content": "System message 1"},
            {"role": "system", "content": "System message 2"},
            {"role": "user", "content": "Hello"},
        ]
    }

    # Mock config with tavern mode enabled
    with (
        patch(
            "xsarena.bridge_v2.api_server.CONFIG",
            {
                "tavern_mode_enabled": True,
                "bypass_enabled": False,
                "id_updater_last_mode": "direct_chat",
                "id_updater_battle_target": "a",
            },
        ),
        patch(
            "xsarena.bridge_v2.api_server.MODEL_NAME_TO_ID_MAP",
            {"test-model": "test-id"},
        ),
        patch("xsarena.bridge_v2.api_server.MODEL_ENDPOINT_MAP", {}),
    ):
        result = asyncio.run(
            convert_openai_to_lmarena_payload(
                openai_data, 
                "session123", 
                "msg123", 
                "test-model",
                {"test-model": "test-id"},  # model_name_to_id_map
                {},  # model_endpoint_map
                {
                    "tavern_mode_enabled": True,
                    "bypass_enabled": False,
                    "id_updater_last_mode": "direct_chat",
                    "id_updater_battle_target": "a",
                }  # config
            )
        )

    # Check that system messages were merged
    message_templates = result["message_templates"]
    assert len(message_templates) == 2  # One merged system + one user
    assert message_templates[0]["role"] == "system"
    assert "System message 1" in message_templates[0]["content"]
    assert "System message 2" in message_templates[0]["content"]
    assert message_templates[1]["role"] == "user"


def test_bridge_bypass_injection():
    """Test trailing user message injection in bypass mode."""
    # Test data with user message
    openai_data = {
        "messages": [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Hello"},
        ]
    }

    # Mock config with bypass mode enabled
    with (
        patch(
            "xsarena.bridge_v2.api_server.CONFIG",
            {
                "tavern_mode_enabled": False,
                "bypass_enabled": True,
                "id_updater_last_mode": "direct_chat",
                "id_updater_battle_target": "a",
            },
        ),
        patch(
            "xsarena.bridge_v2.api_server.MODEL_NAME_TO_ID_MAP",
            {"test-model": "test-id"},
        ),
        patch("xsarena.bridge_v2.api_server.MODEL_ENDPOINT_MAP", {}),
    ):
        result = asyncio.run(
            convert_openai_to_lmarena_payload(
                openai_data, 
                "session123", 
                "msg123", 
                "test-model",
                {"test-model": "test-id"},  # model_name_to_id_map
                {},  # model_endpoint_map
                {
                    "tavern_mode_enabled": False,
                    "bypass_enabled": True,
                    "id_updater_last_mode": "direct_chat",
                    "id_updater_battle_target": "a",
                }  # config
            )
        )

    # Check that an extra user message with space was added
    message_templates = result["message_templates"]
    assert len(message_templates) >= 3  # system + user + bypass user
    # The last message should be the bypass message
    last_message = message_templates[-1]
    assert last_message["role"] == "user"
    assert last_message["content"] == " "


def test_bridge_participant_positions():
    """Test participantPosition mapping for direct vs battle modes."""
    # Test data
    openai_data = {
        "messages": [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
    }

    # Test direct_chat mode
    with (
        patch(
            "xsarena.bridge_v2.api_server.CONFIG",
            {
                "tavern_mode_enabled": False,
                "bypass_enabled": False,
                "id_updater_last_mode": "direct_chat",
                "id_updater_battle_target": "a",
            },
        ),
        patch(
            "xsarena.bridge_v2.api_server.MODEL_NAME_TO_ID_MAP",
            {"test-model": "test-id"},
        ),
        patch("xsarena.bridge_v2.api_server.MODEL_ENDPOINT_MAP", {}),
    ):
        result = asyncio.run(
            convert_openai_to_lmarena_payload(
                openai_data, 
                "session123", 
                "msg123", 
                "test-model",
                {"test-model": "test-id"},  # model_name_to_id_map
                {},  # model_endpoint_map
                {
                    "tavern_mode_enabled": False,
                    "bypass_enabled": False,
                    "id_updater_last_mode": "direct_chat",
                    "id_updater_battle_target": "a",
                }  # config
            )
        )

    message_templates = result["message_templates"]
    # In direct_chat mode: system -> 'b', user/assistant -> 'a'
    assert (
        message_templates[0]["participantPosition"] == "b"
    )  # system in direct mode gets 'b'
    assert message_templates[1]["participantPosition"] == "a"  # user
    assert message_templates[2]["participantPosition"] == "a"  # assistant

    # Test battle mode
    openai_data_battle = {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
    }

    with (
        patch(
            "xsarena.bridge_v2.api_server.CONFIG",
            {
                "tavern_mode_enabled": False,
                "bypass_enabled": False,
                "id_updater_last_mode": "battle",
                "id_updater_battle_target": "b",
            },
        ),
        patch(
            "xsarena.bridge_v2.api_server.MODEL_NAME_TO_ID_MAP",
            {"test-model": "test-id"},
        ),
        patch("xsarena.bridge_v2.api_server.MODEL_ENDPOINT_MAP", {}),
    ):
        result_battle = asyncio.run(
            convert_openai_to_lmarena_payload(
                openai_data_battle, 
                "session123", 
                "msg123", 
                "test-model",
                {"test-model": "test-id"},  # model_name_to_id_map
                {},  # model_endpoint_map
                {
                    "tavern_mode_enabled": False,
                    "bypass_enabled": False,
                    "id_updater_last_mode": "battle",
                    "id_updater_battle_target": "b",
                }  # config
            )
        )

    message_templates_battle = result_battle["message_templates"]
    # In battle mode: all messages get battle_target position
    for msg in message_templates_battle:
        assert msg["participantPosition"] == "b"


def test_bridge_config_hot_reload():
    """Test that config is reloaded per request via internal endpoint."""
    from unittest.mock import patch
    # This tests that the internal reload endpoint works
    # Need to provide the internal token for authentication
    with patch("xsarena.bridge_v2.handlers.CONFIG", {"internal_api_token": "test-token"}):
        response = client.post("/internal/reload", headers={"x-internal-token": "test-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["reloaded"] is True


def test_bridge_internal_config_health():
    """Test both internal config and health endpoints."""
    from unittest.mock import patch
    # Test /internal/config endpoint
    with patch("xsarena.bridge_v2.handlers.CONFIG", {"internal_api_token": "test-token"}):
        response = client.get("/internal/config", headers={"x-internal-token": "test-token"})
        assert response.status_code == 200
        data = response.json()
        assert "bridge" in data

    # Test /health endpoint (doesn't require authentication)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_bridge_first_message_guard():
    """Test that a fake user message is inserted if first message is assistant."""
    # Test data where first message is assistant
    openai_data = {
        "messages": [
            {"role": "assistant", "content": "Previous response"},
            {"role": "user", "content": "Follow-up"},
        ]
    }

    # Mock config
    with (
        patch(
            "xsarena.bridge_v2.api_server.CONFIG",
            {
                "tavern_mode_enabled": False,
                "bypass_enabled": False,
                "id_updater_last_mode": "direct_chat",
                "id_updater_battle_target": "a",
            },
        ),
        patch(
            "xsarena.bridge_v2.api_server.MODEL_NAME_TO_ID_MAP",
            {"test-model": "test-id"},
        ),
        patch("xsarena.bridge_v2.api_server.MODEL_ENDPOINT_MAP", {}),
    ):
        result = asyncio.run(
            convert_openai_to_lmarena_payload(
                openai_data, 
                "session123", 
                "msg123", 
                "test-model",
                {"test-model": "test-id"},  # model_name_to_id_map
                {},  # model_endpoint_map
                {
                    "tavern_mode_enabled": False,
                    "bypass_enabled": False,
                    "id_updater_last_mode": "direct_chat",
                    "id_updater_battle_target": "a",
                }  # config
            )
        )

    message_templates = result["message_templates"]
    # Should have inserted a fake user message at the beginning
    assert len(message_templates) == 3  # fake user + original assistant + original user
    assert message_templates[0]["role"] == "user"
    assert message_templates[0]["content"] == "Hi"
    assert message_templates[1]["role"] == "assistant"
    assert message_templates[1]["content"] == "Previous response"
