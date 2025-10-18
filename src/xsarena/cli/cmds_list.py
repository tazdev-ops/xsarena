from __future__ import annotations

import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..core.manifest import load_manifest

app = typer.Typer(help="Discover directives (profiles, roles, overlays, templates)")
console = Console()


@app.command("profiles")
def list_profiles():
    """List all available prompt profiles."""
    from ..core.profiles import load_profiles

    profiles = load_profiles()
    table = Table(title="Available Prompt Profiles")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Overlays", style="magenta")
    table.add_column("Description", style="green")
    for name, data in sorted(profiles.items()):
        overlays = ", ".join(data.get("overlays", []))
        desc = (
            data.get("extra", "No description available.").split(".")[0] + "."
        ).strip()
        table.add_row(name, overlays, desc)
    console.print(table)


@app.command("roles")
def list_roles():
    """List roles (manifest first; fallback to filesystem)."""
    man = load_manifest()
    roles = man.get("roles") or []
    rows = []
    if roles:
        for r in roles:
            name = r.get("name", Path(r.get("path", "")).stem.replace("role.", ""))
            summary = r.get("summary", "")
            rows.append((name, summary))
    else:
        # Show warning if manifest is empty
        typer.echo("No entries in manifest. Run: xsarena directives index")
        base = Path("directives/roles")
        if base.exists():
            for role_file in sorted(base.glob("*.md")):
                content = role_file.read_text(encoding="utf-8", errors="ignore")
                first = (
                    (content.splitlines()[:1] or [role_file.stem])[0]
                    .lstrip("# ")
                    .strip()
                )
                rows.append((role_file.stem.replace("role.", ""), first))
    table = Table(title="Roles")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Summary", style="green")
    for n, s in rows:
        table.add_row(n, s)
    console.print(table)


@app.command("overlays")
def list_overlays():
    """List overlays (manifest first; fallback to filesystem)."""
    man = load_manifest()
    overlays = man.get("overlays") or []
    rows = []
    if overlays:
        for o in overlays:
            name = o.get("name", Path(o.get("path", "?")).name)
            headers = o.get("headers", [])
            if headers:
                for header in headers:
                    rows.append((name, header))
            else:
                rows.append((name, "(no OVERLAY headers found)"))
    else:
        # Show warning if manifest is empty
        typer.echo("No entries in manifest. Run: xsarena directives index")
        d = Path("directives")
        if d.exists():
            for p in sorted(d.glob("style.*.md")):
                text = p.read_text(encoding="utf-8", errors="ignore")
                for h in re.findall(r"^OVERLAY:\s*(.+)$", text, flags=re.MULTILINE):
                    rows.append((p.name, h.strip()))
    if not rows:
        typer.echo("(none)")
        return
    table = Table(title="Overlays")
    table.add_column("Source", style="blue")
    table.add_column("Overlay", style="magenta")
    for a, b in rows:
        table.add_row(a, b)
    console.print(table)


@app.command("templates")
def list_templates():
    """List structured templates (prompts) and schema presence."""
    man = load_manifest()
    prompts = man.get("prompts") or []
    rows = []
    if prompts:
        for p in prompts:
            name = p.get("name", Path(p.get("path", "?")).stem)
            schema = p.get("schema")
            rows.append((name, "yes" if schema else "no"))
    else:
        # Show warning if manifest is empty
        typer.echo("No prompts in manifest. Run: xsarena directives index")
        # fallback: scan filesystem for *.json.md
        for p in list(Path("directives").glob("**/*.json.md")) + list(
            Path("directives").glob("**/prompt.*.json.md")
        ):
            sch = Path("data/schemas") / f"{p.stem}.schema.json"
            rows.append((p.stem, "yes" if sch.exists() else "no"))
    if not rows:
        typer.echo("(none)")
        return
    table = Table(title="Templates (structured prompts)")
    table.add_column("Name", style="cyan")
    table.add_column("Schema", style="green")
    for n, s in sorted(rows):
        table.add_row(n, s)
    console.print(table)
