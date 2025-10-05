"""Main CLI entry point for LMASudio."""
import typer
import asyncio
from typing import Optional
from ..core.config import Config
from ..core.state import SessionState
from ..core.backends import create_backend
from ..core.engine import Engine

# Import mode handlers
from .cmds_book import app as book_app
from .cmds_lossless import app as lossless_app
from .cmds_backend import app as backend_app
from .cmds_debug import app as debug_app
from .cmds_modes import app as modes_app
from .service import app as service_app

app = typer.Typer()

# Add subcommands for each mode
app.add_typer(book_app, name="book", help="Book authoring commands")
app.add_typer(lossless_app, name="lossless", help="Lossless text processing commands")
app.add_typer(backend_app, name="backend", help="Backend configuration commands")
app.add_typer(debug_app, name="debug", help="Debugging commands")
app.add_typer(modes_app, name="mode", help="Mode toggles and settings")
app.add_typer(service_app, name="service", help="Service management (start servers)")

@app.callback()
def main(
    backend: str = typer.Option("bridge", help="Backend to use (bridge or openrouter)"),
    model: str = typer.Option("default", help="Model to use"),
    window: int = typer.Option(100, help="Window size for history"),
):
    """
    LMASudio - AI-powered writing and coding studio
    """
    # Store configuration in a global context or pass to commands
    pass

def run():
    """Run the CLI application."""
    app()

if __name__ == "__main__":
    run()