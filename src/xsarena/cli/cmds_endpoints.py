# src/xsarena/cli/cmds_endpoints.py
"""Endpoints management commands for XSArena."""
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Manage endpoint configurations from endpoints.yml.")
console = Console()

ENDPOINTS_PATH = Path("endpoints.yml")


@app.command("list")
def list_endpoints():
    """List all available endpoints from endpoints.yml."""
    if not ENDPOINTS_PATH.exists():
        console.print("[yellow]endpoints.yml not found. No endpoints to list.[/yellow]")
        return

    try:
        endpoints_data = (
            yaml.safe_load(ENDPOINTS_PATH.read_text(encoding="utf-8")) or {}
        )
    except Exception as e:
        console.print(f"[red]Error loading endpoints.yml: {e}[/red]")
        raise typer.Exit(1)

    table = Table("Name", "Overlays", "Model", "Backend", title="Available Endpoints")
    for name, config in endpoints_data.items():
        overlays = ", ".join(config.get("overlays", []))
        model = config.get("model", "default")
        backend = config.get("backend", "bridge")
        table.add_row(name, overlays, model, backend)
    console.print(table)


@app.command("show")
def show_endpoint(name: str = typer.Argument(..., help="Name of the endpoint to show")):
    """Show the configuration for a specific endpoint."""
    if not ENDPOINTS_PATH.exists():
        console.print("[red]Error: endpoints.yml not found.[/red]")
        raise typer.Exit(1)

    try:
        endpoints_data = (
            yaml.safe_load(ENDPOINTS_PATH.read_text(encoding="utf-8")) or {}
        )
    except Exception as e:
        console.print(f"[red]Error loading endpoints.yml: {e}[/red]")
        raise typer.Exit(1)

    if name not in endpoints_data:
        console.print(f"[red]Error: endpoint '{name}' not found in endpoints.yml[/red]")
        raise typer.Exit(1)

    config = endpoints_data[name]
    console.print(f"[bold cyan]Configuration for endpoint '{name}':[/bold cyan]")
    table = Table("Key", "Value", box=None)
    for key, value in config.items():
        table.add_row(key, str(value))
    console.print(table)
