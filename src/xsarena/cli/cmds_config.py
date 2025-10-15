"""Configuration management commands for XSArena."""

import typer
from pathlib import Path

from .context import CLIContext
from ..core.config import Config

app = typer.Typer(help="Configuration management")

@app.command("show")
def config_show():
    """Show current configuration."""
    cli: CLIContext = typer.get_current_context().obj
    
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
    typer.echo(f"  API Key: {'Set' if cli.config.api_key else 'Not set (use environment variable)'}")


@app.command("set")
def config_set(
    backend: str = typer.Option(None, "--backend", help="Set backend (bridge or openrouter)"),
    model: str = typer.Option(None, "--model", help="Set default model"),
    base_url: str = typer.Option(None, "--base-url", help="Set base URL for bridge backend"),
    window_size: int = typer.Option(None, "--window-size", help="Set window size for history"),
    anchor_length: int = typer.Option(None, "--anchor-length", help="Set anchor length"),
    continuation_mode: str = typer.Option(None, "--continuation-mode", help="Set continuation mode (anchor, strict, or off)"),
    repetition_threshold: float = typer.Option(None, "--repetition-threshold", help="Set repetition threshold"),
    timeout: int = typer.Option(None, "--timeout", help="Set request timeout"),
    redaction_enabled: bool = typer.Option(None, "--redaction/--no-redaction", help="Enable or disable redaction"),
):
    """Set configuration values."""
    cli: CLIContext = typer.get_current_context().obj
    
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
    
    # Update the config
    for key, value in updates.items():
        setattr(cli.config, key, value)
    
    # Also update the state to reflect the changes
    for key, value in updates.items():
        if hasattr(cli.state, key):
            setattr(cli.state, key, value)
    
    # Save the updated config to file
    config_path = Path(".xsarena/config.yml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    cli.config.save_to_file(str(config_path))
    
    # Save the state as well
    cli.save()
    
    typer.echo("Configuration updated and saved to .xsarena/config.yml")


@app.command("reset")
def config_reset():
    """Reset configuration to defaults."""
    cli: CLIContext = typer.get_current_context().obj
    
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
    config_paths = [".xsarena/config.yml", ".xsarena/config.yaml", "config.yml", "config.yaml"]
    
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