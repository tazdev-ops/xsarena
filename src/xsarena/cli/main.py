"""Main CLI entry point for XSArena."""

import typer

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
    # Build persistent CLI context and stash on typer context
    # Load config with layered precedence: env → CLI flags → .xsarena/config.yml
    cfg = Config.load_with_layered_config()

    # Override with CLI flags if provided
    if backend != "bridge":
        cfg.backend = backend
    if model != "default":
        cfg.model = model
    if window != 100:
        cfg.window_size = window

    cli_ctx = CLIContext.load(cfg)
    # Persist immediate overrides (so switches via flags are remembered)
    cli_ctx.state.backend = cfg.backend
    cli_ctx.state.model = cfg.model
    cli_ctx.state.window_size = cfg.window_size
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
