"""Unified settings commands for XSArena."""

from typing import Optional

import typer

app = typer.Typer(help="Unified settings interface (configuration + controls)")


@app.command("show")
def settings_show(ctx: typer.Context):
    """Show both configuration and controls settings."""
    cli = ctx.obj

    # Show config settings
    typer.echo("=== Configuration Settings (ops settings) ===")
    typer.echo(f"  Backend: {cli.config.backend}")
    typer.echo(f"  Model: {cli.config.model}")
    typer.echo(f"  Base URL: {cli.config.base_url}")
    typer.echo(f"  Window Size: {cli.config.window_size}")
    typer.echo(f"  Anchor Length: {cli.config.anchor_length}")
    typer.echo(
        f"  API Key: {'Set' if cli.config.api_key else 'Not set (use environment variable)'}"
    )

    # Show controls settings
    typer.echo("\n=== Controls Settings (utils settings) ===")
    typer.echo(f"  Output min chars: {cli.state.output_min_chars}")
    typer.echo(f"  Output passes: {cli.state.output_push_max_passes}")
    typer.echo(f"  Continuation mode: {cli.state.continuation_mode}")
    typer.echo(f"  Anchor length: {cli.state.anchor_length}")
    typer.echo(f"  Repetition threshold: {cli.state.repetition_threshold}")
    typer.echo(f"  Repetition warn: {'ON' if cli.state.repetition_warn else 'OFF'}")
    typer.echo(f"  Coverage hammer: {'ON' if cli.state.coverage_hammer_on else 'OFF'}")
    typer.echo(
        f"  Output budget: {'ON' if cli.state.output_budget_snippet_on else 'OFF'}"
    )
    typer.echo(f"  Output push: {'ON' if cli.state.output_push_on else 'OFF'}")


@app.command("set")
def settings_set(
    ctx: typer.Context,
    # Config options
    backend: Optional[str] = typer.Option(
        None, "--backend", help="Set backend (ops settings)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help="Set default model (ops settings)"
    ),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="Set base URL for bridge backend (ops settings)"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="Set API key (ops settings)"
    ),
    # Controls options
    output_min_chars: Optional[int] = typer.Option(
        None, "--output-min-chars", help="Set minimal chars per chunk (utils settings)"
    ),
    output_push_max_passes: Optional[int] = typer.Option(
        None,
        "--output-push-max-passes",
        help="Set max extension steps per chunk (utils settings)",
    ),
    continuation_mode: Optional[str] = typer.Option(
        None, "--continuation-mode", help="Set continuation mode (utils settings)"
    ),
    anchor_length_config: Optional[int] = typer.Option(
        None, "--anchor-length-config", help="Set config anchor length (ops settings)"
    ),
    anchor_length_control: Optional[int] = typer.Option(
        None,
        "--anchor-length-control",
        help="Set control anchor length (utils settings)",
    ),
    repetition_threshold: Optional[float] = typer.Option(
        None,
        "--repetition-threshold",
        help="Set repetition detection threshold (utils settings)",
    ),
    repetition_warn: Optional[bool] = typer.Option(
        None,
        "--repetition-warn/--no-repetition-warn",
        help="Enable or disable repetition warning (utils settings)",
    ),
    coverage_hammer: Optional[bool] = typer.Option(
        None,
        "--coverage-hammer/--no-coverage-hammer",
        help="Enable or disable coverage hammer (utils settings)",
    ),
    output_budget: Optional[bool] = typer.Option(
        None,
        "--output-budget/--no-output-budget",
        help="Enable or disable output budget addendum (utils settings)",
    ),
    output_push: Optional[bool] = typer.Option(
        None,
        "--output-push/--no-output-push",
        help="Enable or disable output pushing (utils settings)",
    ),
):
    """Set configuration or controls settings."""
    cli = ctx.obj

    # Track changes made to each layer
    config_changed = False
    controls_changed = False

    # Handle config settings
    if backend is not None:
        cli.config.backend = backend
        config_changed = True
    if model is not None:
        cli.config.model = model
        config_changed = True
    if base_url is not None:
        cli.config.base_url = base_url
        config_changed = True
    if api_key is not None:
        cli.config.api_key = api_key
        config_changed = True
    if anchor_length_config is not None:
        cli.config.anchor_length = anchor_length_config
        config_changed = True

    # Handle controls settings
    if output_min_chars is not None:
        cli.state.output_min_chars = output_min_chars
        controls_changed = True
    if output_push_max_passes is not None:
        cli.state.output_push_max_passes = output_push_max_passes
        controls_changed = True
    if continuation_mode is not None:
        cli.state.continuation_mode = continuation_mode
        controls_changed = True
    if anchor_length_control is not None:
        cli.state.anchor_length = anchor_length_control
        controls_changed = True
    if repetition_threshold is not None:
        cli.state.repetition_threshold = repetition_threshold
        controls_changed = True
    if repetition_warn is not None:
        cli.state.repetition_warn = repetition_warn
        controls_changed = True
    if coverage_hammer is not None:
        cli.state.coverage_hammer_on = coverage_hammer
        controls_changed = True
    if output_budget is not None:
        cli.state.output_budget_snippet_on = output_budget
        controls_changed = True
    if output_push is not None:
        cli.state.output_push_on = output_push
        controls_changed = True

    # Save changes if any were made
    if config_changed:
        typer.echo("Configuration settings updated (ops settings layer).")
        # Save config to file
        from pathlib import Path

        config_path = Path(".xsarena/config.yml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        cli.config.save_to_file(str(config_path))

    if controls_changed:
        typer.echo("Controls settings updated (utils settings layer).")
        # Save state
        cli.save()

    if not config_changed and not controls_changed:
        typer.echo("No settings were changed. Use --help for available options.")


@app.command("persist")
def settings_persist(ctx: typer.Context):
    """Persist current CLI knobs to .xsarena/config.yml (controls layer) and save config (config layer)."""
    cli = ctx.obj
    s = cli.state

    from pathlib import Path

    import yaml

    # Read current config
    config_path = Path(".xsarena/config.yml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config if it exists
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Create settings dict with current state values (controls layer)
    settings = {
        "output_min_chars": s.output_min_chars,
        "output_push_max_passes": s.output_push_max_passes,
        "continuation_mode": s.continuation_mode,
        "anchor_length": s.anchor_length,
        "repetition_threshold": s.repetition_threshold,
        "repetition_warn": s.repetition_warn,
        "smart_min_enabled": getattr(s, "smart_min_enabled", False),
        "outline_first_enabled": getattr(s, "outline_first_enabled", False),
        "semantic_anchor_enabled": getattr(s, "semantic_anchor_enabled", False),
        "coverage_hammer_on": getattr(s, "coverage_hammer_on", False),
        "output_budget_snippet_on": getattr(s, "output_budget_snippet_on", False),
        "output_push_on": getattr(s, "output_push_on", False),
        "active_profile": getattr(s, "active_profile", None),
        "overlays_active": getattr(s, "overlays_active", []),
    }

    # Remove None values to keep config clean
    settings = {k: v for k, v in settings.items() if v is not None}

    # Save settings under 'settings' key in config
    config["settings"] = settings

    # Write back to config file
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False)

    typer.echo(
        "Controls settings persisted to .xsarena/config.yml under 'settings:' key"
    )

    # Also save the config layer
    cli.config.save_to_file(str(config_path))
    typer.echo("Configuration settings also saved to .xsarena/config.yml")


@app.command("reset")
def settings_reset(ctx: typer.Context):
    """Reset settings from persisted configuration (controls layer) and reload config (config layer)."""
    from pathlib import Path

    import yaml

    from ..core.config import Config

    cli = ctx.obj
    config_path = Path(".xsarena/config.yml")

    if not config_path.exists():
        typer.echo("No .xsarena/config.yml found", err=True)
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    settings = config.get("settings", {})

    if not settings:
        typer.echo("No settings found in .xsarena/config.yml", err=True)
        return

    # Apply settings to current state (controls layer)
    for key, value in settings.items():
        if hasattr(cli.state, key):
            setattr(cli.state, key, value)

    # Save the updated state back to session
    cli.save()

    typer.echo("Controls settings reset from .xsarena/config.yml")
    typer.echo("Values applied:")
    for key, value in settings.items():
        typer.echo(f"  {key}: {value}")

    # Reload config from file (config layer)
    cli.config = Config.load_from_file(".xsarena/config.yml")
    typer.echo("Configuration settings reloaded from .xsarena/config.yml")
