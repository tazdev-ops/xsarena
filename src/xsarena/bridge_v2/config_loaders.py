"""Configuration loading utilities for bridge v2."""

import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)

# Global CONFIG variable - this is what the handlers module expects
CONFIG = {
    "session_id": os.getenv("XSA_SESSION_ID", ""),
    "message_id": os.getenv("XSA_MESSAGE_ID", ""),
    "tavern_mode_enabled": os.getenv("XSA_TAVERN_MODE", "false").lower() == "true",
    "bypass_enabled": os.getenv("XSA_BYPASS_MODE", "false").lower() == "true",
    "file_bed_enabled": os.getenv("XSA_FILE_BED_ENABLED", "false").lower() == "true",
    "use_default_ids_if_mapping_not_found": True,
    "id_updater_last_mode": "direct_chat",
    "id_updater_battle_target": "a",
    "max_internal_post_bytes": 2_000_000,
    "cors_origins": ["*"],
    "enable_idle_restart": os.getenv("XSA_ENABLE_IDLE_RESTART", "false").lower()
    == "true",
    "idle_restart_timeout_seconds": int(os.getenv("XSA_IDLE_RESTART_TIMEOUT", "3600")),
    "stream_response_timeout_seconds": int(os.getenv("XSA_STREAM_TIMEOUT", "360")),
    "api_key": os.getenv("XSA_BRIDGE_API_KEY"),
    "internal_api_token": os.getenv("XSA_INTERNAL_TOKEN", "dev-token-change-me"),
    "version": "2.0.0",
}

MODEL_NAME_TO_ID_MAP = {}
MODEL_ENDPOINT_MAP = {}


def load_config() -> Dict[str, Any]:
    """Load bridge configuration."""
    global CONFIG
    config_path = Path(".xsarena/config.yml")

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f) or {}

            # Update global CONFIG with loaded values
            if loaded_config.get("bridge"):
                CONFIG.update(loaded_config["bridge"])

            # Update with other config values as needed
            for key, value in loaded_config.items():
                if key not in ["bridge"]:
                    CONFIG[key] = value

        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.warning(f"Could not load config file: {e}")

    # Override with environment variables
    CONFIG["session_id"] = os.getenv("XSA_SESSION_ID", CONFIG.get("session_id", ""))
    CONFIG["message_id"] = os.getenv("XSA_MESSAGE_ID", CONFIG.get("message_id", ""))
    CONFIG["tavern_mode_enabled"] = (
        os.getenv(
            "XSA_TAVERN_MODE", str(CONFIG.get("tavern_mode_enabled", "false"))
        ).lower()
        == "true"
    )
    CONFIG["bypass_enabled"] = (
        os.getenv("XSA_BYPASS_MODE", str(CONFIG.get("bypass_enabled", "false"))).lower()
        == "true"
    )
    CONFIG["file_bed_enabled"] = (
        os.getenv(
            "XSA_FILE_BED_ENABLED", str(CONFIG.get("file_bed_enabled", "false"))
        ).lower()
        == "true"
    )
    CONFIG["api_key"] = os.getenv("XSA_BRIDGE_API_KEY", CONFIG.get("api_key"))

    return CONFIG


def load_model_map() -> Dict[str, str]:
    """Load model mapping configuration."""
    global MODEL_NAME_TO_ID_MAP
    models_path = Path("models.json")

    if models_path.exists():
        try:
            import json

            with open(models_path, "r", encoding="utf-8") as f:
                MODEL_NAME_TO_ID_MAP = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load models.json: {e}")
            MODEL_NAME_TO_ID_MAP = {}
    else:
        MODEL_NAME_TO_ID_MAP = {}

    return MODEL_NAME_TO_ID_MAP


def load_model_endpoint_map() -> Dict[str, str]:
    """Load model endpoint mapping."""
    global MODEL_ENDPOINT_MAP
    map_path = Path("model_endpoint_map.json")

    if map_path.exists():
        try:
            import json

            with open(map_path, "r", encoding="utf-8") as f:
                MODEL_ENDPOINT_MAP = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load model_endpoint_map.json: {e}")
            MODEL_ENDPOINT_MAP = {}
    else:
        MODEL_ENDPOINT_MAP = {}

    return MODEL_ENDPOINT_MAP
