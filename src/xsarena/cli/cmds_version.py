"""Version command for XSArena."""

import typer

from .. import __version__

app = typer.Typer(help="Version information for XSArena")


@app.command("version")
def show_version():
    """Show XSArena version."""
    typer.echo(f"XSArena v{__version__}")
