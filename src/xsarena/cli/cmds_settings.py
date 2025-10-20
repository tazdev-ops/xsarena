"""Configuration and backend management commands for XSArena."""

import json
from pathlib import Path
from typing import Optional

import typer
import yaml

from ..core.config import Config
from .context import CLIContext

app = typer.Typer(help="Configuration and backend management")

# --- Config Commands ---


@app.command("config-show")
def config_show(ctx: typer.Context):
    """Show current configuration."""

    cli: CLIContext = ctx.obj

    typer.echo("Current Configuration:")
    typer.echo(f"  Backend: {cli.config.backend}")
    typer.echo(f"  Model: {cli.config.model}")
    typer.echo(f"  Base URL: {cli.config.base_url}")
    typer.echo(f"  Window Size: {cli.config.window_size}")
    typer.echo(f"  Anchor Length: {cli.config.anchor_length}")
    typer.echo(f"  Continuation Mode: {cli.config.continuation_mode}")
    typer.echo(f"  Repetition Threshold: {cli.config.repetition_threshold}")
    typer.echo(f"  Max Retries: {cli.config.max_retries}")
    typer.echo(f"  Timeout: {cli.config.timeout}")
    typer.echo(f"  Redaction Enabled: {cli.config.redaction_enabled}")
    typer.echo(
        f"  API Key: {'Set' if cli.config.api_key else 'Not set (use environment variable)'}"
    )

    # Show bridge-specific config if available
    config_path = Path(".xsarena/config.yml")
    if config_path.exists():
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f) or {}
        bridge_config = yaml_config.get("bridge", {})
        if bridge_config:
            typer.echo("  Bridge Configuration:")
            typer.echo(f"    Session ID: {bridge_config.get('session_id', 'Not set')}")
            typer.echo(f"    Message ID: {bridge_config.get('message_id', 'Not set')}")


@app.command("config-set")
def config_set(
    ctx: typer.Context,
    backend: str = typer.Option(
        None, "--backend", help="Set backend (bridge or openrouter)"
    ),
    model: str = typer.Option(None, "--model", help="Set default model"),
    base_url: str = typer.Option(
        None, "--base-url", help="Set base URL for bridge backend"
    ),
    window_size: int = typer.Option(
        None, "--window-size", help="Set window size for history"
    ),
    anchor_length: int = typer.Option(
        None, "--anchor-length", help="Set anchor length"
    ),
    continuation_mode: str = typer.Option(
        None,
        "--continuation-mode",
        help="Set continuation mode (anchor, strict, or off)",
    ),
    repetition_threshold: float = typer.Option(
        None, "--repetition-threshold", help="Set repetition threshold"
    ),
    timeout: int = typer.Option(None, "--timeout", help="Set request timeout"),
    redaction_enabled: bool = typer.Option(
        None, "--redaction/--no-redaction", help="Enable or disable redaction"
    ),
    bridge_session: str = typer.Option(
        None, "--bridge-session", help="Set bridge session ID"
    ),
    bridge_message: str = typer.Option(
        None, "--bridge-message", help="Set bridge message ID"
    ),
    coverage_hammer: bool = typer.Option(
        None,
        "--coverage-hammer/--no-coverage-hammer",
        help="Enable or disable coverage hammer",
    ),
    output_budget: bool = typer.Option(
        None,
        "--output-budget/--no-output-budget",
        help="Enable or disable output budget addendum",
    ),
    output_push: bool = typer.Option(
        None, "--output-push/--no-output-push", help="Enable or disable output pushing"
    ),
    output_min_chars: int = typer.Option(
        None, "--output-min-chars", help="Set minimal chars per chunk before moving on"
    ),
    output_push_max_passes: int = typer.Option(
        None, "--output-push-max-passes", help="Set max extension steps per chunk"
    ),
    repetition_warn: bool = typer.Option(
        None,
        "--repetition-warn/--no-repetition-warn",
        help="Enable or disable repetition warning",
    ),
):
    """Set configuration values."""
    from ..core.config import Config

    # Load existing config from file, but allow override of specific values
    config = Config.load_from_file(".xsarena/config.yml")

    updates = {}
    if backend is not None:
        updates["backend"] = backend
    if model is not None:
        updates["model"] = model
    if base_url is not None:
        updates["base_url"] = base_url
    if window_size is not None:
        updates["window_size"] = window_size
    if anchor_length is not None:
        updates["anchor_length"] = anchor_length
    if continuation_mode is not None:
        updates["continuation_mode"] = continuation_mode
    if repetition_threshold is not None:
        updates["repetition_threshold"] = repetition_threshold
    if timeout is not None:
        updates["timeout"] = timeout
    if redaction_enabled is not None:
        updates["redaction_enabled"] = redaction_enabled

    # Update the config with new values
    for key, value in updates.items():
        setattr(config, key, value)

    # Create a basic CLIContext to save the config
    # We avoid loading the full context with the problematic backend
    cli: CLIContext = CLIContext.load(cfg=config)

    # Save the updated config to file
    config_path = Path(".xsarena/config.yml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    cli.config.save_to_file(str(config_path))

    # Handle bridge-specific settings (stored in bridge section of YAML)
    if bridge_session or bridge_message:
        # Load existing config YAML
        if config_path.exists():
            with open(config_path, "r") as f:
                yaml_config = yaml.safe_load(f) or {}
        else:
            yaml_config = {}

        # Ensure bridge section exists
        if "bridge" not in yaml_config:
            yaml_config["bridge"] = {}

        # Update bridge IDs if provided
        if bridge_session:
            yaml_config["bridge"]["session_id"] = bridge_session
        if bridge_message:
            yaml_config["bridge"]["message_id"] = bridge_message

        # Write back to YAML
        with open(config_path, "w") as f:
            yaml.safe_dump(yaml_config, f, default_flow_style=False)

        typer.echo(f"Bridge IDs updated in {config_path}")

    # Update CLI state with new values
    cli: CLIContext = ctx.obj  # Use the shared context to update state
    if coverage_hammer is not None:
        cli.state.coverage_hammer_on = coverage_hammer
    if output_budget is not None:
        cli.state.output_budget_snippet_on = output_budget
    if output_push is not None:
        cli.state.output_push_on = output_push
    if output_min_chars is not None:
        cli.state.output_min_chars = output_min_chars
    if output_push_max_passes is not None:
        cli.state.output_push_max_passes = output_push_max_passes
    if repetition_warn is not None:
        cli.state.repetition_warn = repetition_warn

    # Save the state as well
    cli.save()

    typer.echo("Configuration updated and saved to .xsarena/config.yml")


@app.command("config-reset")
def config_reset(ctx: typer.Context):
    """Reset configuration to defaults."""

    cli: CLIContext = ctx.obj

    # Create a new default config
    default_config = Config()

    # Update the CLI context with default values
    cli.config = default_config

    # Save to file
    config_path = Path(".xsarena/config.yml")
    cli.config.save_to_file(str(config_path))

    typer.echo("Configuration reset to defaults and saved to .xsarena/config.yml")


@app.command("config-path")
def config_path():
    """Show configuration file path."""
    config_paths = [
        ".xsarena/config.yml",
        ".xsarena/config.yaml",
        "config.yml",
        "config.yaml",
    ]

    found_paths = []
    for path in config_paths:
        if Path(path).exists():
            found_paths.append(path)

    if found_paths:
        typer.echo("Found configuration files:")
        for path in found_paths:
            typer.echo(f"  - {path}")
    else:
        typer.echo("No configuration files found. Default config is used.")
        typer.echo("To create a config file, use: xsarena config set --backend bridge")


@app.command("config-export")
def config_export(
    ctx: typer.Context, out: str = typer.Option(".xsarena/config.backup.yml", "--out")
):
    """Export current config to a file."""
    cli: CLIContext = ctx.obj
    cli.config.save_to_file(out)
    typer.echo(f"✓ Exported config to {out}")


@app.command("config-import")
def config_import(
    ctx: typer.Context, inp: str = typer.Option(".xsarena/config.backup.yml", "--in")
):
    """Import config from file; normalizes base_url to /v1."""
    p = Path(inp)
    if not p.exists():
        typer.echo(f"Error: file not found: {inp}")
        raise typer.Exit(1)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    cli: CLIContext = ctx.obj
    for k, v in data.items():
        if hasattr(cli.config, k):
            setattr(cli.config, k, v)
    if cli.config.base_url and not cli.config.base_url.rstrip("/").endswith("/v1"):
        cli.config.base_url = cli.config.base_url.rstrip("/") + "/v1"
    cli.save()
    typer.echo("✓ Imported config")


@app.command("config-check")
def config_check(
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress narrative output"),
):
    """Validate configuration and show any issues."""
    try:
        # Load config with validation
        config = Config.load_with_layered_config()

        # Check for config file and validate its keys
        config_path = Path(".xsarena/config.yml")
        unknown_keys = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}

            # Validate the file config keys
            unknown_keys = Config.validate_config_keys(file_config)

        if json_output:
            result = {
                "valid": True,
                "normalized_base_url": config.base_url,
                "unknown_config_keys": unknown_keys,
            }
            typer.echo(json.dumps(result))
        else:
            if unknown_keys:
                if not quiet:
                    typer.echo(
                        "[yellow]Warning: Unknown config keys in .xsarena/config.yml:[/yellow]"
                    )
                    for key, suggestions in unknown_keys.items():
                        if suggestions:
                            typer.echo(
                                f"  [yellow]{key}[/yellow] (did you mean: {', '.join(suggestions[:2])}?)"
                            )
                        else:
                            typer.echo(f"  [yellow]{key}[/yellow]")

            if not quiet:
                typer.echo("✓ Configuration is valid")
                typer.echo(f"  Base URL normalized to: {config.base_url}")

    except Exception as e:
        if json_output:
            typer.echo(json.dumps({"valid": False, "error": str(e)}))
        else:
            typer.echo(f"[red]✗ Configuration validation failed:[/red] {e}")
        raise typer.Exit(1)


@app.command("config-capture-ids")
def config_capture_ids(ctx: typer.Context):
    """Capture bridge session and message IDs from LMArena."""
    from ..utils.helpers import capture_bridge_ids

    # Get the CLI context to access the configuration
    cli = ctx.obj

    # Compute base URL from config using utility function
    from ..utils.project_paths import base_from_config_url
    base = base_from_config_url(cli.config.base_url)
    
    typer.echo("To capture bridge IDs:")
    typer.echo("1. Make sure the bridge is running (xsarena service start-bridge-v2)")
    typer.echo("2. Open https://lmarena.ai and add '#bridge=5102' to the URL")
    typer.echo("3. Click 'Retry' on any message to activate the tab")
    typer.echo("4. Press ENTER here when ready...")

    try:
        input()
    except KeyboardInterrupt:
        raise typer.Exit(1)

    try:
        session_id, message_id = capture_bridge_ids(base)
        
        # IDs found, update config file
        config_path = Path(".xsarena/config.yml")
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config if it exists
        existing_config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                existing_config = yaml.safe_load(f) or {}

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

        typer.echo("✓ Successfully captured and saved IDs:")
        typer.echo(f"  Session ID: {session_id}")
        typer.echo(f"  Message ID: {message_id}")
        typer.echo(f"  Config saved to: {config_path}")
        return
    except Exception as e:
        typer.echo(f"✗ Error capturing IDs: {e}")
        raise typer.Exit(1)


# --- Backend Commands ---


@app.command("backend-set")
def set_backend(
    ctx: typer.Context,
    backend_type: str = typer.Argument(..., help="Backend type (bridge or openrouter)"),
    api_key: Optional[str] = typer.Option(None, help="API key for openrouter backend"),
    model: Optional[str] = typer.Option(None, help="Model to use"),
    base_url: Optional[str] = typer.Option(None, help="Base URL for bridge backend"),
):
    """Set backend configuration (persistent)."""
    cli: CLIContext = ctx.obj
    cli.state.backend = backend_type
    if model:
        cli.state.model = model
    if api_key:
        cli.config.api_key = api_key  # not persisted to disk; use env or secrets store
        typer.echo(
            "⚠️  API key set in-memory only, not persisted to disk. Use environment variable XSA_API_KEY or secrets store for persistence."
        )
    if base_url:
        cli.config.base_url = base_url
    cli.rebuild_engine()
    cli.save()
    typer.echo(f"Backend: {cli.state.backend}")
    typer.echo(f"Model: {cli.state.model}")
    typer.echo(f"Base URL: {cli.config.base_url}")


@app.command("backend-show")
def show_backend(ctx: typer.Context):
    """Show current backend configuration."""
    cli: CLIContext = ctx.obj
    typer.echo("Current Backend Configuration:")
    typer.echo(f"  Backend: {cli.state.backend}")
    typer.echo(f"  Model: {cli.state.model}")
    typer.echo(f"  Base URL: {cli.config.base_url}")
    typer.echo(f"  API Key: {'Set' if cli.config.api_key else 'Not set'}")


@app.command("backend-test")
def test_backend(ctx: typer.Context):
    """Test the current backend configuration."""
    cli: CLIContext = ctx.obj
    try:
        cli.rebuild_engine()
        typer.echo(f"Backend {cli.state.backend} configured successfully")
        typer.echo("Backend test: Configuration valid")
    except Exception as e:
        typer.echo(f"Backend test failed: {str(e)}")
        raise typer.Exit(code=1)
