# src/xsarena/cli/cmds_macros.py
from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(help="Manage CLI command macros.")
MACROS_PATH = Path(".xsarena/macros.json")


def _load_macros() -> dict:
    if MACROS_PATH.exists():
        return json.loads(MACROS_PATH.read_text(encoding="utf-8"))
    return {}


def _save_macros(macros: dict):
    MACROS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MACROS_PATH.write_text(json.dumps(macros, indent=2))


@app.command("add")
def add_macro(name: str, command: str):
    """Add or update a macro."""
    macros = _load_macros()
    macros[name] = command
    _save_macros(macros)
    typer.echo(f"Macro '{name}' saved.")


@app.command("list")
def list_macros():
    """List all saved macros."""
    macros = _load_macros()
    if not macros:
        typer.echo("No macros defined.")
        return
    for name, command in macros.items():
        typer.echo(f"{name}: {command}")


@app.command("delete")
def delete_macro(name: str):
    """Delete a macro."""
    macros = _load_macros()
    if name in macros:
        del macros[name]
        _save_macros(macros)
        typer.echo(f"Macro '{name}' deleted.")
    else:
        typer.echo(f"Error: Macro '{name}' not found.", err=True)
        raise typer.Exit(1)
