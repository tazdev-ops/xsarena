"""Mode toggle CLI commands for LMASudio."""

import typer

from ..core.config import Config
from ..core.state import SessionState

app = typer.Typer()


@app.command("mode")
def set_mode(mode: str = typer.Argument(..., help="Set mode to 'direct' or 'battle'")):
    """Set the conversation mode (direct or battle)."""
    if mode not in ["direct", "battle"]:
        typer.echo("Mode must be 'direct' or 'battle'")
        raise typer.Exit(code=1)

    # This would update the session state to use appropriate participant positions
    # For now, just acknowledge the mode change
    typer.echo(f"Mode set to: {mode}")

    if mode == "battle":
        typer.echo("Battle mode enabled: responses will use participant positions A/B")


@app.command("battle-target")
def set_battle_target(
    target: str = typer.Argument(..., help="Set battle target to 'A' or 'B'")
):
    """Set the battle target (A or B)."""
    if target.upper() not in ["A", "B"]:
        typer.echo("Target must be 'A' or 'B'")
        raise typer.Exit(code=1)

    typer.echo(f"Battle target set to: {target.upper()}")


@app.command("tavern")
def set_tavern_mode(
    enabled: bool = typer.Argument(
        ..., help="Enable or disable tavern mode (True/False)"
    )
):
    """Enable or disable tavern mode (merge multiple system messages)."""
    if enabled:
        typer.echo("Tavern mode enabled: Multiple system messages will be merged")
    else:
        typer.echo("Tavern mode disabled: Single system message per request")


@app.command("bypass")
def set_bypass_mode(
    enabled: bool = typer.Argument(
        ..., help="Enable or disable bypass mode (True/False)"
    )
):
    """Enable or disable bypass mode (inject extra user message to bypass filters)."""
    if enabled:
        typer.echo(
            "Bypass mode enabled: Extra user message will be added to bypass filters"
        )
    else:
        typer.echo("Bypass mode disabled")


@app.command("image-handling")
def set_image_handling(
    enabled: bool = typer.Argument(
        ..., help="Enable or disable image handling (True/False)"
    )
):
    """Enable or disable image handling (parse a2 image streams)."""
    if enabled:
        typer.echo(
            "Image handling enabled: a2 image streams will be converted to markdown format"
        )
    else:
        typer.echo("Image handling disabled")


@app.command("update-models")
def update_available_models():
    """Update available models from userscript data."""
    typer.echo(
        "Model update endpoint ready. The userscript can POST page HTML to /internal/update_available_models to update available_models.json"
    )


@app.command("session-info")
def show_session_info():
    """Show current session information."""
    config = Config()
    state = SessionState()

    typer.echo("Current Session Information:")
    typer.echo(f"  Backend: {config.backend}")
    typer.echo(f"  Model: {config.model}")
    typer.echo(f"  Window Size: {config.window_size}")
    typer.echo(f"  Continuation Mode: {state.continuation_mode}")
    typer.echo(f"  Anchor Length: {state.anchor_length}")
    typer.echo(f"  Repetition Threshold: {state.repetition_threshold}")
    typer.echo(f"  History Length: {len(state.history)}")
