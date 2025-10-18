from __future__ import annotations

import re
from pathlib import Path

import typer
import yaml
from rich.console import Console

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
