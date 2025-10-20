"""
Unified settings commands for XSArena.
"""
import time
from pathlib import Path

import typer
import yaml

app = typer.Typer(help="Unified settings interface (configuration + controls)")


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
    try:
        import requests
    except ImportError:
        typer.echo(
            "Error: 'requests' library is required for capture-ids but is not installed."
        )
        raise typer.Exit(1)

    # POST /internal/start_id_capture
    try:
        response = requests.post("http://localhost:5102/internal/start_id_capture")
        if response.status_code != 200:
            typer.echo(f"Failed to start ID capture: {response.status_code}")
            raise typer.Exit(1)
        typer.echo("Started ID capture process...")
    except requests.exceptions.ConnectionError:
        typer.echo("Error: Could not connect to bridge server at http://localhost:5102")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error starting ID capture: {e}")
        raise typer.Exit(1)

    # Poll GET /internal/config until bridge.session_id/message_id appear (timeout ~90s)
    timeout = 90  # seconds
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get("http://localhost:5102/internal/config")
            if response.status_code == 200:
                config_data = response.json()
                bridge_config = config_data.get("bridge", {})
                session_id = bridge_config.get("session_id")
                message_id = bridge_config.get("message_id")

                if session_id and message_id:
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
            else:
                typer.echo(
                    f"Polling... server returned {response.status_code}, waiting for IDs..."
                )
        except requests.exceptions.ConnectionError:
            typer.echo("Polling... connection error, waiting for server...")
        except Exception as e:
            typer.echo(f"Polling... error: {e}, waiting for IDs...")

        time.sleep(2)  # Wait 2 seconds before next poll

    typer.echo("Timeout: Failed to capture IDs within 90 seconds.")
    raise typer.Exit(1)
