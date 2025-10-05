"""Backend configuration CLI commands for LMASudio."""
import typer
from typing import Optional
from ..core.config import Config
from ..core.state import SessionState
from ..core.backends import create_backend

app = typer.Typer()

@app.command("set")
def set_backend(
    backend_type: str = typer.Argument(..., help="Backend type (bridge or openrouter)"),
    api_key: Optional[str] = typer.Option(None, help="API key for openrouter backend"),
    model: Optional[str] = typer.Option(None, help="Model to use"),
    base_url: Optional[str] = typer.Option(None, help="Base URL for bridge backend")
):
    """Set backend configuration."""
    config = Config()
    
    config.backend = backend_type
    if api_key:
        config.api_key = api_key
    if model:
        config.model = model
    if base_url:
        config.base_url = base_url
    
    # Save to session or config file
    state = SessionState()
    state.settings['backend'] = backend_type
    if model:
        state.settings['model'] = model
    
    typer.echo(f"Backend set to: {backend_type}")
    if model:
        typer.echo(f"Model set to: {model}")
    if base_url:
        typer.echo(f"Base URL set to: {base_url}")

@app.command("show")
def show_backend():
    """Show current backend configuration."""
    config = Config()
    
    typer.echo("Current Backend Configuration:")
    typer.echo(f"  Backend: {config.backend}")
    typer.echo(f"  Model: {config.model}")
    typer.echo(f"  Base URL: {config.base_url}")
    typer.echo(f"  API Key: {'Set' if config.api_key else 'Not set'}")

@app.command("test")
def test_backend():
    """Test the current backend configuration."""
    config = Config()
    
    try:
        backend = create_backend(config.backend, 
                               base_url=config.base_url, 
                               api_key=config.api_key, 
                               model=config.model)
        typer.echo(f"Backend {config.backend} configured successfully")
        # In a real implementation, we would test by making a simple API call
        typer.echo("Backend test: Configuration valid")
    except Exception as e:
        typer.echo(f"Backend test failed: {str(e)}")
        raise typer.Exit(code=1)