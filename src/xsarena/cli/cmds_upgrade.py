# src/xsarena/cli/cmds_upgrade.py
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Version-aware upgrader: check for and apply required fixes.")
console = Console()


@app.command("check")
def check_for_upgrades():
    """Check for available upgrade packs and necessary code modifications."""
    table = Table(title="Available Upgrades")
    table.add_column("ID", style="cyan")
    table.add_column("Description", style="magenta")
    table.add_column("Status", style="green")
    table.add_row("UPGRADE-001", "Refactor interactive command wiring", "Available")
    console.print(table)


@app.command("apply")
def apply_upgrades(
    dry_run: bool = typer.Option(
        True, "--dry-run/--apply", help="Show changes without applying them."
    ),
):
    """Apply available upgrade packs."""
    if dry_run:
        console.print("[yellow]DRY RUN MODE[/yellow]: No changes will be made.")
        console.print("Proposed changes for [cyan]UPGRADE-001[/cyan]:")
        console.print(
            "  - [green]ADD[/green] `cmds_interactive.py` and wire into `main.py`"
        )
    else:
        console.print(
            "[green]Applying upgrade packs...[/green] (This is a placeholder action)"
        )
