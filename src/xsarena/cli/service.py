"""
Service commands for XSArena bridge.
"""
import typer

from ..bridge_v2.api_server import run_server

app = typer.Typer(help="Service management commands.")


@app.command("start-bridge-v2")
def start_bridge_v2():
    """
    Start the bridge v2 server.
    """
    run_server()
