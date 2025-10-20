from __future__ import annotations

import re
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from ..utils.discovery import list_overlays, list_roles

app = typer.Typer(help="Directive utilities")
console = Console()


def _get_file_summary(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("<!--"):
                return line.lstrip("# ").strip()
    except Exception:
        pass
    return ""


def _get_overlay_headers(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return re.findall(r"^OVERLAY:\s*(.+)$", text, flags=re.MULTILINE)
    except Exception:
        return []


@app.command("index")
def directives_index(out: str = typer.Option("directives/manifest.yml", "--out")):
    """Scan directives/ and generate a rich manifest.yml with metadata."""
    console.print(f"[bold]Indexing directives into {out}...[/bold]")
    base = Path("directives")
    roles = []
    prompts = []
    overlays = []
    if base.exists():
        # roles
        for p in base.glob("roles/**/*.md"):
            name = p.stem.replace("role.", "")
            summary = _get_file_summary(p)
            roles.append({"name": name, "path": str(p), "summary": summary})
        # prompts (json.md and prompt.*.json.md)
        for p in list(base.glob("**/*.json.md")) + list(
            base.glob("**/prompt.*.json.md")
        ):
            schema = Path("data/schemas") / f"{p.stem}.schema.json"
            prompts.append(
                {
                    "name": p.stem,
                    "path": str(p),
                    "schema": str(schema) if schema.exists() else None,
                }
            )
        # overlays from style.*.md
        for p in base.glob("style.*.md"):
            headers = _get_overlay_headers(p)
            if headers:
                overlays.append(
                    {
                        "name": p.name,
                        "path": str(p),
                        "headers": [h.strip() for h in headers],
                    }
                )
    manifest = {"roles": roles, "prompts": prompts, "overlays": overlays}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    console.print(
        f"[green]✓ Indexed {len(roles)} roles, {len(prompts)} prompts, {len(overlays)} style files.[/green]"
    )


@app.command("roles")
def roles_list():
    """List all available roles."""
    roles = list_roles()
    if not roles:
        console.print("[yellow]No roles found.[/yellow]")
        return

    table = Table(title="Available Roles")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Source", style="magenta")
    table.add_column("Preview", style="green")

    for role in roles:
        table.add_row(role["name"], role["source"], role["content_preview"])

    console.print(table)


@app.command("overlays")
def overlays_list():
    """List all available overlays."""
    overlays = list_overlays()
    if not overlays:
        console.print("[yellow]No overlays found.[/yellow]")
        return

    table = Table(title="Available Overlays")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Source", style="magenta")
    table.add_column("Preview", style="green")

    for overlay in overlays:
        table.add_row(overlay["name"], overlay["source"], overlay["content_preview"])

    console.print(table)


@app.command("roles-show")
def roles_show(name: str):
    """Show the content of a specific role."""
    roles = list_roles()
    # Handle both cases: with and without extension
    role_name = name
    if name.endswith(".md"):
        role_name = name[:-3]  # Remove .md extension
    role = next((r for r in roles if r["name"] == role_name), None)
    if not role:
        console.print(f"[red]Role '{name}' not found.[/red]")
        return

    console.print(
        f"[bold blue]Role: {name}[/bold blue]"
    )  # Use original name for display
    console.print(role["content_preview"])


@app.command("overlays-show")
def overlays_show(name: str):
    """Show the content of a specific overlay."""
    overlays = list_overlays()
    # Handle both cases: with and without extension
    overlay_name = name
    if name.endswith(".md"):
        overlay_name = name[:-3]  # Remove .md extension
    overlay = next((o for o in overlays if o["name"] == overlay_name), None)
    if not overlay:
        console.print(f"[red]Overlay '{name}' not found.[/red]")
        return

    console.print(
        f"[bold blue]Overlay: {name}[/bold blue]"
    )  # Use original name for display
    console.print(overlay["content_preview"])
