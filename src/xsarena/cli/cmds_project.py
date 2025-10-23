"""Project management commands for XSArena."""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml

from .project.dedupe import app as dedupe_app
from .project.docs import app as docs_app
from .project.init import app as init_app

app = typer.Typer(help="Project management commands")

# Add sub-apps
app.add_typer(dedupe_app, name="dedupe")
app.add_typer(init_app, name="init")
app.add_typer(docs_app, name="docs")


@app.command("config-migrate")
def config_migrate():
    """Migrate from config.jsonc/models.json/model_endpoint_map.json to .xsarena/config.yml."""
    migrated = []

    # Load from old config files if they exist
    old_configs = {}

    if Path("config.jsonc").exists():
        with open("config.jsonc", "r") as f:
            # Handle JSONC (JSON with comments) by removing comments
            content = f.read()
            # Remove lines starting with // (comments)
            lines = [
                line
                for line in content.splitlines()
                if not line.strip().startswith("//")
            ]
            content = "\n".join(lines)
            old_configs["bridge"] = json.loads(content)
            migrated.append("config.jsonc")

    if Path("models.json").exists():
        with open("models.json", "r") as f:
            old_configs["models"] = json.load(f)
            migrated.append("models.json")

    if Path("model_endpoint_map.json").exists():
        with open("model_endpoint_map.json", "r") as f:
            old_configs["model_endpoint_map"] = json.load(f)
            migrated.append("model_endpoint_map.json")

    # Write to .xsarena/config.yml under bridge section
    config_path = Path(".xsarena/config.yml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config if it exists
    if config_path.exists():
        with open(config_path, "r") as f:
            existing_config = yaml.safe_load(f) or {}
    else:
        existing_config = {}

    # Merge old configs into existing config
    for key, value in old_configs.items():
        existing_config[key] = value

    with open(config_path, "w") as f:
        yaml.safe_dump(existing_config, f, default_flow_style=False)

    typer.echo(
        f"Migrated: {', '.join(migrated) if migrated else 'No config files found'}"
    )
    typer.echo(f"Updated: {config_path}")
    typer.echo("Note: Original files kept in place (deprecated).")


@app.command("bridge-ids")
def bridge_ids(
    set_cmd: bool = typer.Option(
        False, "--set", help="Set bridge session and message IDs"
    ),
    get_cmd: bool = typer.Option(
        False, "--get", help="Get bridge session and message IDs"
    ),
    session: Optional[str] = typer.Option(None, "--session", help="Session ID"),
    message: Optional[str] = typer.Option(None, "--message", help="Message ID"),
):
    """Manage bridge session and message IDs."""
    config_path = Path(".xsarena/config.yml")

    if get_cmd:
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
            bridge_config = config.get("bridge", {})
            session_id = bridge_config.get("session_id")
            message_id = bridge_config.get("message_id")
            typer.echo(f"Session ID: {session_id}")
            typer.echo(f"Message ID: {message_id}")
        else:
            typer.echo("No .xsarena/config.yml found")
        return

    if set_cmd:
        if not session or not message:
            typer.echo(
                "Error: Both --session and --message are required for set command"
            )
            raise typer.Exit(code=1)

        # Load existing config
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Update bridge section
        if "bridge" not in config:
            config["bridge"] = {}
        config["bridge"]["session_id"] = session
        config["bridge"]["message_id"] = message

        # Write back
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        typer.echo(f"Updated bridge IDs in {config_path}")
        typer.echo(f"Session ID: {session}")
        typer.echo(f"Message ID: {message}")


@app.command("bridge-flags")
def bridge_flags(
    tavern: Optional[str] = typer.Option(
        None, "--tavern", help="Enable/disable tavern mode (on/off)"
    ),
    bypass: Optional[str] = typer.Option(
        None, "--bypass", help="Enable/disable bypass mode (on/off)"
    ),
    idle: Optional[str] = typer.Option(
        None, "--idle", help="Enable/disable idle restart (on/off)"
    ),
    timeout: Optional[int] = typer.Option(
        None, "--timeout", help="Stream response timeout in seconds"
    ),
):
    """Manage bridge configuration flags."""
    config_path = Path(".xsarena/config.yml")

    # Load existing config
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Ensure bridge section exists
    if "bridge" not in config:
        config["bridge"] = {}

    # Update flags if provided
    updates = []

    if tavern is not None:
        if tavern.lower() in ["on", "true", "1", "yes"]:
            config["bridge"]["tavern_mode_enabled"] = True
            updates.append("tavern_mode_enabled = true")
        elif tavern.lower() in ["off", "false", "0", "no"]:
            config["bridge"]["tavern_mode_enabled"] = False
            updates.append("tavern_mode_enabled = false")
        else:
            typer.echo("Error: --tavern must be 'on' or 'off'")
            raise typer.Exit(code=1)

    if bypass is not None:
        if bypass.lower() in ["on", "true", "1", "yes"]:
            config["bridge"]["bypass_enabled"] = True
            updates.append("bypass_enabled = true")
        elif bypass.lower() in ["off", "false", "0", "no"]:
            config["bridge"]["bypass_enabled"] = False
            updates.append("bypass_enabled = false")
        else:
            typer.echo("Error: --bypass must be 'on' or 'off'")
            raise typer.Exit(code=1)

    if idle is not None:
        if idle.lower() in ["on", "true", "1", "yes"]:
            config["bridge"]["enable_idle_restart"] = True
            updates.append("enable_idle_restart = true")
        elif idle.lower() in ["off", "false", "0", "no"]:
            config["bridge"]["enable_idle_restart"] = False
            updates.append("enable_idle_restart = false")
        else:
            typer.echo("Error: --idle must be 'on' or 'off'")
            raise typer.Exit(code=1)

    if timeout is not None:
        if timeout < 0:
            typer.echo("Error: --timeout must be a non-negative integer")
            raise typer.Exit(code=1)
        config["bridge"]["stream_response_timeout_seconds"] = timeout
        updates.append(f"stream_response_timeout_seconds = {timeout}")

    # Write back to config file
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)

    typer.echo(f"Updated bridge flags in {config_path}")
    for update in updates:
        typer.echo(f"  {update}")


@app.command("normalize")
def normalize():
    """Apply content fixes and cleanup (normalize, declutter)."""
    typer.echo("Applying normalization and cleanup...")

    # Apply content fixes (similar to apply_content_fixes.sh)
    for root, dirs, files in os.walk("."):
        # Skip certain directories
        dirs[:] = [
            d
            for d in dirs
            if d not in [".git", ".venv", "venv", "__pycache__", ".xsarena"]
        ]

        for file in files:
            if file.endswith((".py", ".md", ".txt", ".json", ".yml", ".yaml")):
                filepath = Path(root) / file
                try:
                    content = filepath.read_text(encoding="utf-8")
                    # Apply basic fixes like removing trailing whitespace
                    lines = content.splitlines()
                    fixed_lines = [line.rstrip() for line in lines]
                    fixed_content = "\n".join(fixed_lines)

                    if content != fixed_content:
                        filepath.write_text(fixed_content, encoding="utf-8")
                        typer.echo(f"Fixed: {filepath}")
                except Exception:
                    pass  # Skip files that can't be read

    # Apply declutter (similar to declutter_phase2.sh)
    # Remove common temp files
    temp_patterns = ["*.tmp", "*.temp", "*.bak", "*~", ".DS_Store"]
    for pattern in temp_patterns:
        for temp_file in Path(".").glob(f"**/{pattern}"):
            try:
                temp_file.unlink()
                typer.echo(f"Removed: {temp_file}")
            except Exception:
                pass

    typer.echo("Normalization and cleanup complete.")


@app.command("directives-merge")
def directives_merge():
    """Merge session rules from directives/_rules into directives/_rules/rules.merged.md."""
    typer.echo("Merging session rules...")

    rules_dir = Path("directives/_rules")
    sources_dir = rules_dir / "sources"
    output_file = rules_dir / "rules.merged.md"

    if not sources_dir.exists():
        typer.echo("Sources directory not found.")
        return

    merged_content = []
    for source_file in sources_dir.glob("*.md"):
        try:
            content = source_file.read_text(encoding="utf-8")
            merged_content.append(f"<!-- Source: {source_file.name} -->\n")
            merged_content.append(content)
            merged_content.append("\n---\n\n")  # Separator
        except Exception as e:
            typer.echo(f"Error reading {source_file}: {e}")

    if merged_content:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("".join(merged_content), encoding="utf-8")
        typer.echo(f"Merged rules to: {output_file}")

    # Run deduplication if the script exists
    dedupe_script = Path("tools/dedupe_rules_merged.py")
    if dedupe_script.exists():
        import subprocess

        try:
            result = subprocess.run(
                [sys.executable, str(dedupe_script)], capture_output=True, text=True
            )
            if result.returncode == 0:
                typer.echo("Rules deduplication completed.")
            else:
                typer.echo(f"Deduplication failed: {result.stderr}")
        except Exception as e:
            typer.echo(f"Error running deduplication: {e}")


if __name__ == "__main__":
    app()
