import typer

from .context import CLIContext

app = typer.Typer(help="Fine-tune output, continuation, and repetition behavior.")


@app.command("hammer")
def coverage_hammer(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Toggle the coverage hammer (prevents premature summarization)."""
    cli: CLIContext = ctx.obj
    cli.state.coverage_hammer_on = enable
    cli.save()
    typer.echo(f"Coverage hammer: {'ON' if enable else 'OFF'}")


@app.command("budget")
def output_budget(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Toggle the output budget addendum (pushes for longer chunks)."""
    cli: CLIContext = ctx.obj
    cli.state.output_budget_snippet_on = enable
    cli.save()
    typer.echo(f"Output budget addendum: {'ON' if enable else 'OFF'}")


@app.command("push")
def output_push(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Toggle output push (micro-extends to meet min_chars)."""
    cli: CLIContext = ctx.obj
    cli.state.output_push_on = enable
    cli.save()
    typer.echo(f"Output push: {'ON' if enable else 'OFF'}")


@app.command("minchars")
def output_minchars(
    ctx: typer.Context,
    n: int = typer.Argument(..., help="Minimum characters per chunk."),
):
    """Set the target minimum characters per chunk (e.g., 4500)."""
    cli: CLIContext = ctx.obj
    cli.state.output_min_chars = max(3000, n)
    cli.save()
    typer.echo(f"Output min chars set to: {cli.state.output_min_chars}")


@app.command("passes")
def output_passes(
    ctx: typer.Context, n: int = typer.Argument(..., help="Max micro-extend passes.")
):
    """Set the max number of micro-extend passes per chunk (0-5)."""
    cli: CLIContext = ctx.obj
    cli.state.output_push_max_passes = max(0, min(10, n))
    cli.save()
    typer.echo(f"Output push max passes set to: {cli.state.output_push_max_passes}")


@app.command("cont-anchor")
def cont_anchor(
    ctx: typer.Context,
    n: int = typer.Argument(..., help="Length of text anchor in characters."),
):
    """Set the continuation anchor length (e.g., 300)."""
    cli: CLIContext = ctx.obj
    cli.state.anchor_length = max(50, min(2000, n))
    cli.save()
    typer.echo(f"Anchor length set to: {cli.state.anchor_length}")


@app.command("repeat-warn")
def repeat_warn(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Toggle the repetition detection warning."""
    cli: CLIContext = ctx.obj
    cli.state.repetition_warn = enable
    cli.save()
    typer.echo(f"Repetition warning: {'ON' if enable else 'OFF'}")


@app.command("repeat-thresh")
def repeat_thresh(
    ctx: typer.Context,
    threshold: float = typer.Argument(
        ..., help="Jaccard similarity threshold (0.0-1.0)."
    ),
):
    """Set the repetition detection threshold (e.g., 0.35)."""
    cli: CLIContext = ctx.obj
    if 0 < threshold < 1:
        cli.state.repetition_threshold = threshold
        cli.save()
        typer.echo(f"Repetition threshold set to: {cli.state.repetition_threshold}")
    else:
        typer.echo("Error: threshold must be between 0.0 and 1.0", err=True)


@app.command("smart-min")
def smart_min(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Toggle token-aware minimum length scaling (scales min_chars by token estimator)."""
    cli: CLIContext = ctx.obj
    cli.state.smart_min_enabled = enable
    cli.save()
    typer.echo(f"Smart min (token-aware): {'ON' if enable else 'OFF'}")


@app.command("outline-first")
def outline_first(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Toggle outline-first seed for the first chunk only (then removed)."""
    cli: CLIContext = ctx.obj
    cli.state.outline_first_enabled = enable
    cli.save()
    typer.echo(f"Outline-first toggle: {'ON' if enable else 'OFF'}")


@app.command("cont-mode")
def cont_mode(
    ctx: typer.Context,
    mode: str = typer.Argument(..., help="'anchor', 'normal', or 'semantic-anchor'."),
):
    """Set the continuation strategy."""
    cli: CLIContext = ctx.obj
    mode_lower = mode.lower()

    # Normalize synonyms
    if mode_lower == "strict":
        mode_lower = "anchor"
    elif mode_lower == "off":
        mode_lower = "normal"
    elif mode_lower == "semantic":
        mode_lower = "semantic-anchor"

    if mode_lower in ["anchor", "normal", "semantic-anchor"]:
        cli.state.continuation_mode = mode_lower
        # Set semantic anchor flag based on mode
        if mode_lower == "semantic-anchor":
            cli.state.semantic_anchor_enabled = True
        else:
            cli.state.semantic_anchor_enabled = False
        cli.save()
        typer.echo(f"Continuation mode set to: {cli.state.continuation_mode}")
    else:
        typer.echo(
            "Error: mode must be 'anchor', 'normal', 'semantic-anchor', 'strict', 'off', or 'semantic'",
            err=True,
        )


@app.command("persist")
def settings_persist(ctx: typer.Context):
    """Persist current CLI knobs to .xsarena/config.yml under settings: key."""
    from pathlib import Path

    import yaml

    cli: CLIContext = ctx.obj
    s = cli.state

    # Read current config
    config_path = Path(".xsarena/config.yml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config if it exists
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Create settings dict with current state values
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
        "active_profile": getattr(s, "active_profile", None),
        "overlays_active": getattr(s, "overlays_active", []),
    }

    # Remove None values to keep config clean
    settings = {k: v for k, v in settings.items() if v is not None}

    # Save settings under 'settings' key in config
    config["settings"] = settings

    # Write back to config file
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False)

    typer.echo("Settings persisted to .xsarena/config.yml under 'settings:' key")
    typer.echo("Values saved:")
    for key, value in settings.items():
        typer.echo(f"  {key}: {value}")


@app.command("reset")
def settings_reset(ctx: typer.Context):
    """Reset CLI knobs from persisted settings in .xsarena/config.yml."""
    from pathlib import Path

    import yaml

    cli: CLIContext = ctx.obj
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

    # Apply settings to current state
    for key, value in settings.items():
        if hasattr(cli.state, key):
            setattr(cli.state, key, value)

    # Save the updated state back to session
    cli.save()

    typer.echo("Settings reset from .xsarena/config.yml")
    typer.echo("Values applied:")
    for key, value in settings.items():
        typer.echo(f"  {key}: {value}")


@app.command("show")
def controls_show(ctx: typer.Context):
    """Show current continuation/output/repetition knobs."""
    cli: CLIContext = ctx.obj
    s = cli.state

    typer.echo("Controls:")
    typer.echo(f"  Output min chars: {s.output_min_chars}")
    typer.echo(f"  Output passes: {s.output_push_max_passes}")
    typer.echo(f"  Continuation mode: {s.continuation_mode}")
    typer.echo(f"  Anchor length: {s.anchor_length}")
    typer.echo(f"  Repetition threshold: {s.repetition_threshold}")
    typer.echo(f"  Repetition warn: {'ON' if s.repetition_warn else 'OFF'}")
    typer.echo(
        f"  Smart min: {'ON' if getattr(s, 'smart_min_enabled', False) else 'OFF'}"
    )
    typer.echo(
        f"  Outline-first: {'ON' if getattr(s, 'outline_first_enabled', False) else 'OFF'}"
    )
    typer.echo(
        f"  Semantic anchor: {'ON' if getattr(s, 'semantic_anchor_enabled', False) else 'ON'}"
    )

    # Add token budget estimation
    from ..utils.token_estimator import chars_to_tokens_approx

    estimated_tokens = chars_to_tokens_approx(s.output_min_chars)

    # Typical model limits

    # Use a reasonable default for common models
    conservative_limit = 8000  # GPT-4 level limit

    if estimated_tokens > conservative_limit * 0.8:  # 80% of limit
        budget_status = "HIGH (may hit token limits)"
        advice = "Consider lowering min_chars to avoid early cutoffs"
    elif estimated_tokens > conservative_limit * 0.6:  # 60% of limit
        budget_status = "MODERATE (aggressive but likely OK)"
        advice = "Should work for most models, but monitor for cutoffs"
    else:
        budget_status = "OK (within typical limits)"
        advice = "Should fit comfortably in most models' response budgets"

    typer.echo(f"  Estimated tokens per chunk: ~{estimated_tokens}")
    typer.echo(f"  Budget estimate: {budget_status}")
    typer.echo(f"  Tip: {advice}")
