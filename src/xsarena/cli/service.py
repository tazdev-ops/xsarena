"""Service management CLI for XSArena."""

import os
import subprocess
import sys

import typer

app = typer.Typer()


@app.command("start-bridge")
def start_bridge(
    port: int = typer.Option(5102, "--port", "-p", help="Port for the bridge server"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host for the bridge server"),
):
    """Start the bridge server on a specific port (defaults to v2)."""
    typer.echo("⚠️  DEPRECATION WARNING: Use 'xsarena service start-bridge-v2' instead.")
    env = os.environ.copy()
    cmd = [sys.executable, "-m", "xsarena.bridge_v2.api_server"]
    typer.echo(
        f"Starting bridge v2 server on {host}:{port} (redirected from legacy command)"
    )
    env["PORT"] = str(port)
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        typer.echo("\nBridge v2 server stopped")





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
    env["XSA_COMPAT_PORT"] = str(port)
    env["XSA_HOST"] = host

    cmd = [
        sys.executable,
        "-m",
        "xsarena.bridge.compat_server",
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
   xsarena service start-bridge --port 8080  # Instance 1
   xsarena service start-bridge --port 8081  # Instance 2
   xsarena service start-bridge --port 8082  # Instance 3

2. In your browser tabs, configure the userscript to use specific ports:
   - Tab A: Add #bridge=8080 to the URL
   - Tab B: Add #bridge=8081 to the URL
   - Tab C: Add #bridge=8082 to the URL

3. Or use the devtools helper in each tab:
   In Tab B DevTools: lmaSetBridgePort(8081)

4. Each instance maintains its own session state independently.

5. You can also start the compatibility API servers on different ports:
   xsarena service start-compat-api --port 8000
   xsarena service start-compat-api --port 8001
"""
    typer.echo(help_text)


@app.command("start-bridge-v2")
def start_bridge_v2(
    port: int = typer.Option(5102, "--port", "-p"),
    host: str = typer.Option("127.0.0.1", "--host"),
):
    """Start the bridge v2 (WS + SSE) server."""
    env = os.environ.copy()
    cmd = [sys.executable, "-m", "xsarena.bridge_v2.api_server"]
    typer.echo(f"Starting bridge v2 on {host}:{port}")
    env["PORT"] = str(port)
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        typer.echo("\nBridge v2 stopped")


@app.command("start-id-updater")
def start_id_updater():
    """Start the ID updater helper (captures session/message IDs from browser)."""
    cmd = [sys.executable, "tools/id_updater.py"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        typer.echo("\nID Updater stopped")


if __name__ == "__main__":
    app()
