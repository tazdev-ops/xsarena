"""Main CLI entry point for XSArena."""

import typer
from click.core import ParameterSource

from ..core.config import Config
from .context import CLIContext
from .registry import app


@app.callback()
def main(
    ctx: typer.Context,
    backend: str = typer.Option("bridge", help="Backend to use (bridge or openrouter)"),
    model: str = typer.Option("default", help="Model to use"),
    window: int = typer.Option(100, help="Window size for history"),
):
    """
    XSArena - AI-powered writing and coding studio

    XSArena uses Bridge-first architecture by default. This means it connects to a local
    bridge server that relays requests to the actual LMArena backend through your browser.
    """
    cfg = Config.load_with_layered_config()
    # Determine which options were explicitly provided
    ps = ctx.get_parameter_source
    overrides = {}
    if ps("backend") == ParameterSource.COMMANDLINE:
        overrides["backend"] = backend
    if ps("model") == ParameterSource.COMMANDLINE:
        overrides["model"] = model
    if ps("window") == ParameterSource.COMMANDLINE:
        overrides["window_size"] = window
    # Load context with original config
    cli_ctx = CLIContext.load(cfg, state_path=None)

    # Apply overrides explicitly (highest precedence) - this was the original bug location
    if overrides.get("backend"):
        cli_ctx.state.backend = overrides["backend"]
    if overrides.get("model"):
        cli_ctx.state.model = overrides["model"]
    if overrides.get("window_size") is not None:
        cli_ctx.state.window_size = overrides["window_size"]

    # DO NOT reset state to config values (this was the original bug):
    # cli_ctx.state.backend = cfg.backend
    # cli_ctx.state.model = cfg.model
    # cli_ctx.state.window_size = cfg.window_size

    # Only rebuild engine if backend changed to avoid issues with missing API keys
    # This prevents the immediate failure when switching to backends without proper config
    # The engine will be properly configured when actually used with correct credentials
    cli_ctx.save()
    ctx.obj = cli_ctx


@app.command("version")
def _version():
    from .. import __version__

    typer.echo(f"XSArena v{__version__}")


def run():
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()
