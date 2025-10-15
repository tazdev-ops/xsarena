"""Backend configuration CLI commands for XSArena."""

from typing import Optional

import typer

from .context import CLIContext

app = typer.Typer()


@app.command("set")
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
    if base_url:
        cli.config.base_url = base_url
    cli.rebuild_engine()
    cli.save()
    typer.echo(f"Backend: {cli.state.backend}")
    typer.echo(f"Model: {cli.state.model}")
    typer.echo(f"Base URL: {cli.config.base_url}")


@app.command("show")
def show_backend(ctx: typer.Context):
    """Show current backend configuration."""
    cli: CLIContext = ctx.obj
    typer.echo("Current Backend Configuration:")
    typer.echo(f"  Backend: {cli.state.backend}")
    typer.echo(f"  Model: {cli.state.model}")
    typer.echo(f"  Base URL: {cli.config.base_url}")
    typer.echo(f"  API Key: {'Set' if cli.config.api_key else 'Not set'}")


@app.command("test")
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
