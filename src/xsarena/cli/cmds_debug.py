"""Debugging CLI commands for XSArena."""

import typer

from ..core.state import SessionState
from .context import CLIContext

app = typer.Typer()


@app.command("state")
def show_state(ctx: typer.Context):
    """Show current session state."""
    cli: CLIContext = ctx.obj
    state = cli.state

    typer.echo("Session State:")
    typer.echo(f"  History length: {len(state.history)}")
    typer.echo(f"  Anchors: {len(state.anchors)}")
    typer.echo(f"  Continuation Mode: {state.continuation_mode}")
    typer.echo(f"  Anchor Length: {state.anchor_length}")
    typer.echo(f"  Repetition Threshold: {state.repetition_threshold}")
    typer.echo(f"  Backend: {state.backend}")
    typer.echo(f"  Model: {state.model}")
    typer.echo(f"  Window Size: {state.window_size}")
    typer.echo(f"  Current Job ID: {getattr(state, 'current_job_id', 'N/A')}")
    jq = getattr(state, "job_queue", [])
    typer.echo(f"  Job Queue Length: {len(jq) if isinstance(jq, (list, tuple)) else 0}")
    typer.echo(f"  Redaction Enabled: {state.settings.get('redaction_enabled', False)}")


@app.command("clear-history")
def clear_history(ctx: typer.Context):
    """Clear the conversation history."""
    cli: CLIContext = ctx.obj
    cli.state.history.clear()
    cli.save()
    typer.echo("Conversation history cleared")


@app.command("clear-anchors")
def clear_anchors(ctx: typer.Context):
    """Clear the anchors."""
    cli: CLIContext = ctx.obj
    cli.state.anchors.clear()
    cli.save()
    typer.echo("Anchors cleared")


@app.command("config")
def show_config(ctx: typer.Context):
    """Show current configuration."""
    cli: CLIContext = ctx.obj
    config = cli.config

    typer.echo("Current Configuration:")
    typer.echo(f"  Backend: {config.backend}")
    typer.echo(f"  Model: {config.model}")
    typer.echo(f"  Window Size: {config.window_size}")
    typer.echo(f"  Anchor Length: {config.anchor_length}")
    typer.echo(f"  Continuation Mode: {config.continuation_mode}")
    typer.echo(f"  Repetition Threshold: {config.repetition_threshold}")
    typer.echo(f"  Max Retries: {config.max_retries}")
    typer.echo(f"  API Key: {'Set' if config.api_key else 'Not set'}")
    typer.echo(f"  Base URL: {config.base_url}")
    typer.echo(f"  Timeout: {config.timeout}")
    typer.echo(f"  Redaction Enabled: {config.redaction_enabled}")


@app.command("save-state")
def save_state(
    ctx: typer.Context,
    filepath: str = typer.Argument(
        "./.xsarena/session_state.json", help="Path to save state file"
    ),
):
    """Save current state to a file."""
    cli: CLIContext = ctx.obj
    cli.state.save_to_file(filepath)
    typer.echo(f"State saved to {filepath}")


@app.command("load-state")
def load_state(
    ctx: typer.Context,
    filepath: str = typer.Argument(
        "./.xsarena/session_state.json", help="Path to load state file"
    ),
):
    """Load state from a file."""
    cli: CLIContext = ctx.obj
    cli.state = SessionState.load_from_file(filepath)
    # In a real implementation, we would update the active session with this state
    typer.echo(f"State loaded from {filepath}")
    typer.echo(f"Loaded state has history length: {len(cli.state.history)}")


@app.command("toggle-redaction")
def toggle_redaction(
    ctx: typer.Context,
    enabled: bool = typer.Argument(..., help="Enable or disable redaction filter"),
):
    """Toggle the redaction filter."""
    cli: CLIContext = ctx.obj

    # Set the redaction setting in the state
    cli.state.settings["redaction_enabled"] = enabled

    if enabled:
        # Import the redact function from core.redact module
        try:
            from ..core.redact import redact

            cli.engine.set_redaction_filter(redact)
            typer.echo(
                "Redaction filter enabled: sensitive information will be filtered"
            )
        except ImportError:
            typer.echo("Redaction filter enabled but redact module not available")
    else:
        cli.engine.set_redaction_filter(None)
        typer.echo("Redaction filter disabled")

    # Save the state
    cli.save()
