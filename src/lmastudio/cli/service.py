"""Service management CLI for LMASudio."""

import os
import subprocess
import sys

import typer

app = typer.Typer()


@app.command("start-bridge")
def start_bridge(
    port: int = typer.Option(8080, "--port", "-p", help="Port for the bridge server"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host for the bridge server"),
):
    """Start the bridge server on a specific port."""
    env = os.environ.copy()
    env["LMA_PORT"] = str(port)
    env["LMA_HOST"] = host

    cmd = [
        sys.executable,
        "-m",
        "src.lmastudio.bridge.server",
        "--port",
        str(port),
        "--host",
        host,
    ]

    typer.echo(f"Starting bridge server on {host}:{port}")
    typer.echo(f"Command: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        typer.echo("\nBridge server stopped")


@app.command("start-compat-api")
def start_compat_api(
    port: int = typer.Option(
        8000, "--port", "-p", help="Port for the compatibility API server"
    ),
    host: str = typer.Option(
        "127.0.0.1", "--host", help="Host for the compatibility API server"
    ),
):
    """Start the OpenAI-compatible API server on a specific port."""
    env = os.environ.copy()
    env["LMA_COMPAT_PORT"] = str(port)
    env["LMA_HOST"] = host

    cmd = [
        sys.executable,
        "-m",
        "src.lmastudio.bridge.compat_server",
        "--port",
        str(port),
        "--host",
        host,
    ]

    typer.echo(f"Starting compatibility API server on {host}:{port}")
    typer.echo(f"Command: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        typer.echo("\nCompatibility API server stopped")


@app.command("multi-instance-help")
def multi_instance_help():
    """Show help for running multiple instances."""
    help_text = """
Multi-instance Usage Guide:

1. Start multiple bridge servers on different ports:
   lmastudio service start-bridge --port 8080  # Instance 1
   lmastudio service start-bridge --port 8081  # Instance 2
   lmastudio service start-bridge --port 8082  # Instance 3

2. In your browser tabs, configure the userscript to use specific ports:
   - Tab A: Add #bridge=8080 to the URL
   - Tab B: Add #bridge=8081 to the URL
   - Tab C: Add #bridge=8082 to the URL

3. Or use the devtools helper in each tab:
   In Tab B DevTools: lmaSetBridgePort(8081)

4. Each instance maintains its own session state independently.

5. You can also start the compatibility API servers on different ports:
   lmastudio service start-compat-api --port 8000
   lmastudio service start-compat-api --port 8001
"""
    typer.echo(help_text)


if __name__ == "__main__":
    app()
