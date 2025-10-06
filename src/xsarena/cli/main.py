"""Main CLI entry point for XSArena."""

import typer

from .cmds_backend import app as backend_app

# Import mode handlers
from .cmds_book import app as book_app
from .cmds_debug import app as debug_app
from .cmds_lossless import app as lossless_app
from .cmds_modes import app as modes_app
from .cmds_pipeline import app as pipeline_app
from .service import app as service_app

app = typer.Typer()

# Add subcommands for each mode
app.add_typer(book_app, name="book", help="Book authoring commands")
app.add_typer(lossless_app, name="lossless", help="Lossless text processing commands")
app.add_typer(backend_app, name="backend", help="Backend configuration commands")
app.add_typer(debug_app, name="debug", help="Debugging commands")
app.add_typer(modes_app, name="mode", help="Mode toggles and settings")
app.add_typer(service_app, name="service", help="Service management (start servers)")
app.add_typer(
    pipeline_app, name="pipeline", help="Pipeline runner (fix → test → format → commit)"
)


@app.callback()
def main(
    backend: str = typer.Option("bridge", help="Backend to use (bridge or openrouter)"),
    model: str = typer.Option("default", help="Model to use"),
    window: int = typer.Option(100, help="Window size for history"),
):
    """
    XSArena - AI-powered writing and coding studio
    """
    # Store configuration in a global context or pass to commands
    pass


def run():
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()
