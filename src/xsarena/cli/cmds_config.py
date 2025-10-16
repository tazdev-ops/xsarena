"""Configuration management commands for XSArena."""

from pathlib import Path

import typer
import yaml

from ..core.config import Config
from .context import CLIContext

app = typer.Typer(help="Configuration management")


@app.command("show")
def config_show():
    """Show current configuration."""

    cli: CLIContext = CLIContext.load()

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


@app.command("set")
def config_set(
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
        None, "--coverage-hammer/--no-coverage-hammer", help="Enable or disable coverage hammer"
    ),
    output_budget: bool = typer.Option(
        None, "--output-budget/--no-output-budget", help="Enable or disable output budget addendum"
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
        None, "--repetition-warn/--no-repetition-warn", help="Enable or disable repetition warning"
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


@app.command("reset")
def config_reset():
    """Reset configuration to defaults."""

    cli: CLIContext = CLIContext.load()

    # Create a new default config
    default_config = Config()

    # Update the CLI context with default values
    cli.config = default_config

    # Save to file
    config_path = Path(".xsarena/config.yml")
    cli.config.save_to_file(str(config_path))

    typer.echo("Configuration reset to defaults and saved to .xsarena/config.yml")


@app.command("path")
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
