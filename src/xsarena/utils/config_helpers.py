"""
Simple configuration helpers for XSArena.
Consolidates configuration to 2 main files:
- .xsarena/config.yml - project settings
- .xsarena/session_state.json - user session state
"""
import json
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config() -> Dict[str, Any]:
    """Load merged config from config.yml + session_state.json"""
    config_dict = {}

    # Load main config file
    config_path = Path(".xsarena/config.yml")
    if config_path.exists():
        try:
            config_dict.update(
                yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            )
        except Exception as e:
            print(f"Warning: Could not load .xsarena/config.yml: {e}")

    # Load session state if it exists
    session_path = Path(".xsarena/session_state.json")
    if session_path.exists():
        try:
            session_data = json.loads(session_path.read_text(encoding="utf-8"))
            # Merge session state into config with a namespace
            config_dict["session"] = session_data
        except Exception as e:
            print(f"Warning: Could not load .xsarena/session_state.json: {e}")

    return config_dict


def save_config(config_dict: Dict[str, Any]) -> None:
    """Save config back to files"""
    # Create .xsarena directory if it doesn't exist
    xsarena_dir = Path(".xsarena")
    xsarena_dir.mkdir(exist_ok=True)

    # Separate session data from main config
    session_data = config_dict.get("session", {})
    main_config = {k: v for k, v in config_dict.items() if k != "session"}

    # Save main config
    config_path = xsarena_dir / "config.yml"
    config_path.write_text(
        yaml.safe_dump(main_config, sort_keys=False), encoding="utf-8"
    )

    # Save session state
    if session_data:
        session_path = xsarena_dir / "session_state.json"
        session_path.write_text(json.dumps(session_data, indent=2), encoding="utf-8")
