"""Mode toggle CLI commands for XSArena."""

import typer

from .context import CLIContext
from ..core.config import Config
from ..core.state import SessionState

app = typer.Typer()


@app.command("mode")
def set_mode(mode: str = typer.Argument(..., help="Set mode to 'direct' or 'battle'")):
    """Set the conversation mode (direct or battle)."""
    cli: CLIContext = typer.get_current_context().obj
    typer.echo("Feature is stubbed; no effect.")


@app.command("battle-target")
def set_battle_target(
    target: str = typer.Argument(..., help="Set battle target to 'A' or 'B'")
):
    """Set the battle target (A or B)."""
    cli: CLIContext = typer.get_current_context().obj
    typer.echo("Feature is stubbed; no effect.")


@app.command("tavern")
def set_tavern_mode(
    enabled: bool = typer.Argument(
        ..., help="Enable or disable tavern mode (True/False)"
    )
):
    """Enable or disable tavern mode (merge multiple system messages)."""
    cli: CLIContext = typer.get_current_context().obj
    typer.echo("Feature is stubbed; no effect.")


@app.command("bypass")
def set_bypass_mode(
    enabled: bool = typer.Argument(
        ..., help="Enable or disable bypass mode (True/False)"
    )
):
    """Enable or disable bypass mode (inject extra user message to bypass filters)."""
    cli: CLIContext = typer.get_current_context().obj
    typer.echo("Feature is stubbed; no effect.")


@app.command("image-handling")
def set_image_handling(
    enabled: bool = typer.Argument(
        ..., help="Enable or disable image handling (True/False)"
    )
):
    """Enable or disable image handling (parse a2 image streams)."""
    cli: CLIContext = typer.get_current_context().obj
    typer.echo("Feature is stubbed; no effect.")


@app.command("update-models")
def update_available_models():
    """Update available models from userscript data."""
    cli: CLIContext = typer.get_current_context().obj
    typer.echo(
        "Model update endpoint ready. The userscript can POST page HTML to /internal/update_available_models to update available_models.json"
    )


@app.command("session-info")
def show_session_info():
    """Show current session information."""
    cli: CLIContext = typer.get_current_context().obj
    config = cli.config
    state = cli.state

    typer.echo("Current Session Information:")
    typer.echo(f"  Backend: {config.backend}")
    typer.echo(f"  Model: {config.model}")
    typer.echo(f"  Window Size: {config.window_size}")
    typer.echo(f"  Continuation Mode: {state.continuation_mode}")
    typer.echo(f"  Anchor Length: {state.anchor_length}")
    typer.echo(f"  Repetition Threshold: {state.repetition_threshold}")
    typer.echo(f"  History Length: {len(state.history)}")
    typer.echo(f"  Redaction Enabled: {state.settings.get('redaction_enabled', False)}")
