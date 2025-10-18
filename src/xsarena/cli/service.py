"""Service management CLI for XSArena."""

import os
import signal
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
    typer.echo(
        "⚠️  DEPRECATION WARNING: Use 'xsarena service start-bridge-v2' instead."
    )
    env = os.environ.copy()
    cmd = [sys.executable, "-m", "xsarena.bridge_v2.api_server"]
    typer.echo(
        f"Starting bridge v2 server on {host}:{port} (redirected from legacy command)"
    )
    env["PORT"] = str(port)
    try:
        process = subprocess.Popen(cmd, env=env)
        process.wait()
    except KeyboardInterrupt:
        typer.echo("\nStopping Bridge v2 server...")
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
        except subprocess.TimeoutExpired:
            typer.echo("Forcefully terminating...")
            process.terminate()
            process.wait()
        typer.echo("Bridge v2 server stopped")


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
    try:
        import importlib

        importlib.import_module("xsarena.bridge.compat_server")
    except ImportError:
        typer.echo(
            "Error: The compatibility API server module (xsarena.bridge.compat_server) is not available.",
            err=True,
        )
        typer.echo(
            "This usually means you are missing a dependency. Please check your installation.",
            err=True,
        )
        raise typer.Exit(code=1)

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
        process = subprocess.Popen(cmd, env=env)
        process.wait()
    except KeyboardInterrupt:
        typer.echo("\nStopping Compatibility API server...")
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
        except subprocess.TimeoutExpired:
            typer.echo("Forcefully terminating...")
            process.terminate()
            process.wait()
        typer.echo("Compatibility API server stopped")


@app.command("multi-instance-help")
def multi_instance_help():
    """Show help for running multiple instances."""
    help_text = """
Multi-instance Usage Guide:

1. Start multiple bridge servers on different ports:
   xsarena service start-bridge-v2 --port 5102  # Instance 1 (default)
   xsarena service start-bridge-v2 --port 5103  # Instance 2
   xsarena service start-bridge-v2 --port 5104  # Instance 3

2. In your browser tabs, configure the userscript to use specific ports:
   - Tab A: Add #bridge=5102 to the URL
   - Tab B: Add #bridge=5103 to the URL
   - Tab C: Add #bridge=5104 to the URL

3. Or use the devtools helper in each tab:
   In Tab B DevTools: lmaSetBridgePort(5103)

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
        process = subprocess.Popen(cmd, env=env)
        process.wait()
    except KeyboardInterrupt:
        typer.echo("\nStopping Bridge v2...")
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
        except subprocess.TimeoutExpired:
            typer.echo("Forcefully terminating...")
            process.terminate()
            process.wait()
        typer.echo("Bridge v2 stopped")


@app.command("start-id-updater")
def start_id_updater():
    """Start the ID updater helper (captures session/message IDs from browser)."""
    import os

    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "tools",
        "id_updater.py",
    )
    cmd = [sys.executable, script_path]
    try:
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        typer.echo("\nStopping ID Updater...")
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
        except subprocess.TimeoutExpired:
            typer.echo("Forcefully terminating...")
            process.terminate()
            process.wait()
        typer.echo("ID Updater stopped")


@app.command("install-bridge")
def install_bridge():
    """Install systemd service file for the bridge server."""
    import os
    from pathlib import Path

    # Create the systemd user directory if it doesn't exist
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    # Define the service file content
    service_content = """[Unit]
Description=XSArena Bridge Server
After=network.target

[Service]
Type=simple
ExecStart={python_path} -m xsarena.bridge_v2.api_server
Restart=always
RestartSec=5
Environment=PORT=5102
WorkingDirectory={work_dir}

[Install]
WantedBy=default.target
""".format(
        python_path=sys.executable, work_dir=os.getcwd()
    )

    # Write the service file
    service_file = systemd_dir / "xsarena-bridge.service"
    with open(service_file, "w") as f:
        f.write(service_content)

    typer.echo(f"✓ Service file installed: {service_file}")
    typer.echo("")
    typer.echo("To manage the service, use:")
    typer.echo("  systemctl --user daemon-reload    # Reload systemd configuration")
    typer.echo("  systemctl --user enable xsarena-bridge  # Enable auto-start on boot")
    typer.echo("  systemctl --user start xsarena-bridge   # Start the service")
    typer.echo("  systemctl --user stop xsarena-bridge    # Stop the service")
    typer.echo("  systemctl --user status xsarena-bridge  # Check service status")
    typer.echo("  journalctl --user -u xsarena-bridge     # View logs")


@app.command("start")
def service_start(
    service_name: str = typer.Argument(..., help="Service to start (bridge)")
):
    """Start a service using systemctl --user."""
    if service_name == "bridge":
        result = subprocess.run(
            ["systemctl", "--user", "start", "xsarena-bridge"], check=False
        )
        if result.returncode == 0:
            typer.echo("✓ Bridge service started")
        else:
            typer.echo("❌ Failed to start bridge service", err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"❌ Unknown service: {service_name}", err=True)
        raise typer.Exit(code=1)


@app.command("stop")
def service_stop(
    service_name: str = typer.Argument(..., help="Service to stop (bridge)")
):
    """Stop a service using systemctl --user."""
    if service_name == "bridge":
        result = subprocess.run(
            ["systemctl", "--user", "stop", "xsarena-bridge"], check=False
        )
        if result.returncode == 0:
            typer.echo("✓ Bridge service stopped")
        else:
            typer.echo("❌ Failed to stop bridge service", err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"❌ Unknown service: {service_name}", err=True)
        raise typer.Exit(code=1)


@app.command("status")
def service_status(
    service_name: str = typer.Argument(..., help="Service to check status (bridge)")
):
    """Check status of a service using systemctl --user."""
    if service_name == "bridge":
        result = subprocess.run(
            ["systemctl", "--user", "status", "xsarena-bridge"], check=False
        )
        if result.returncode != 0:
            typer.echo("❌ Failed to get service status", err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"❌ Unknown service: {service_name}", err=True)
        raise typer.Exit(code=1)


@app.command("enable")
def service_enable(
    service_name: str = typer.Argument(..., help="Service to enable (bridge)")
):
    """Enable a service to start on boot using systemctl --user."""
    if service_name == "bridge":
        result = subprocess.run(
            ["systemctl", "--user", "enable", "xsarena-bridge"], check=False
        )
        if result.returncode == 0:
            typer.echo("✓ Bridge service enabled")
        else:
            typer.echo("❌ Failed to enable bridge service", err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"❌ Unknown service: {service_name}", err=True)
        raise typer.Exit(code=1)


@app.command("disable")
def service_disable(
    service_name: str = typer.Argument(..., help="Service to disable (bridge)")
):
    """Disable a service from starting on boot using systemctl --user."""
    if service_name == "bridge":
        result = subprocess.run(
            ["systemctl", "--user", "disable", "xsarena-bridge"], check=False
        )
        if result.returncode == 0:
            typer.echo("✓ Bridge service disabled")
        else:
            typer.echo("❌ Failed to disable bridge service", err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo(f"❌ Unknown service: {service_name}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
