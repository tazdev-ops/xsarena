# Main CLI entry point for xsarena
"""This module provides the main command-line interface for xsarena."""
import typer

from .registry import app


@app.command("version")
def _version():
    from .. import __version__

    typer.echo(f"XSArena v{__version__}")


def run():
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()
