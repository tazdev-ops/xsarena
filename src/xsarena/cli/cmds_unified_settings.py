"""
Unified settings commands for XSArena.
"""
import os
import time
from pathlib import Path

import typer
import yaml

from ..utils.project_paths import base_from_config_url

app = typer.Typer(help="Unified settings interface (configuration + controls)")


def _load_base_url():
    """Load the base URL from config file."""
    config_path = Path(".xsarena/config.yml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        # Get base_url from the main config section, not bridge section
        base_url = config.get("base_url", "http://localhost:5102")
    else:
        base_url = "http://localhost:5102"  # Default fallback
    # Use utility function to strip /v1 if present
    return base_from_config_url(base_url)


@app.command("show")
def show_settings():
    """
    Show current settings from .xsarena/config.yml if present.
    """
    config_path = Path(".xsarena/config.yml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        print(yaml.dump(config, default_flow_style=False, sort_keys=False))
    else:
        typer.echo("No .xsarena/config.yml file found.")


@app.command("capture-ids")
def capture_ids():
    """
    Capture bridge session and message IDs by POSTing to /internal/start_id_capture,
    polling GET /internal/config until bridge.session_id/message_id appear (timeout ~90s),
    and persisting under bridge: {session_id, message_id} in .xsarena/config.yml.
    """
    from ..utils.helpers import capture_bridge_ids

    # Compute base URL from config
    base = _load_base_url()
    
    try:
        session_id, message_id = capture_bridge_ids(base)
        typer.echo(f"Captured session_id: {session_id}")
        typer.echo(f"Captured message_id: {message_id}")

        # Persist under bridge: {session_id, message_id} in .xsarena/config.yml
        config_path = Path(".xsarena/config.yml")
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config if it exists
        existing_config = {}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    existing_config = yaml.safe_load(f) or {}
            except (FileNotFoundError, yaml.YAMLError):
                pass  # If config file is invalid, start with empty dict

        # Update the bridge section with the new IDs
        if "bridge" not in existing_config:
            existing_config["bridge"] = {}
        existing_config["bridge"]["session_id"] = session_id
        existing_config["bridge"]["message_id"] = message_id

        # Save the updated config
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                existing_config,
                f,
                default_flow_style=False,
                sort_keys=False,
            )

        typer.echo(f"IDs saved to {config_path}")
        return
    except Exception as e:
        typer.echo(f"Error capturing IDs: {e}")
        raise typer.Exit(1)
