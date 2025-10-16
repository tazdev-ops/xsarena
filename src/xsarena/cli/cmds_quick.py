from __future__ import annotations

from pathlib import Path
from typing import List

import typer


from ..core.prompt import compose_prompt
from ..core.specs import DEFAULT_PROFILES, LENGTH_PRESETS, SPAN_PRESETS
from .context import CLIContext

app = typer.Typer(
    help="Quick launcher: wait for capture, then run a long, dense book with curated profiles"
)


def _slugify(s: str) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "book"


@app.command("start")
def quick_start(
    ctx: typer.Context,
    subject: str = typer.Argument(..., help="Book subject"),
    profile: str = typer.Option(
        "",
        "--profile",
        help="Preset: clinical-masters|elections-focus|compressed-handbook|pop-explainer|bilingual-pairs",
    ),
    length: str = typer.Option(
        "long", "--length", help="Per-message length: standard|long|very-long|max"
    ),
    span: str = typer.Option("book", "--span", help="Total span: medium|long|book"),
    out_path: str = typer.Option(
        "", "--out", "-o", help="Output path (defaults to books/finals/<slug>.final.md)"
    ),
    wait: bool = typer.Option(
        True,
        "--wait/--no-wait",
        help="Prompt to wait for browser capture before starting",
    ),
    extra_file: List[str] = typer.Option(
        [],
        "--extra-file",
        "-E",
        help="Append file(s) to system prompt (e.g., directives/_rules/rules.merged.md)",
    ),
):
    """DEPRECATED: Use 'xsarena run book' instead."""
    typer.echo("⚠️  DEPRECATED: Use 'xsarena run book' instead.")
    
    # Map quick parameters to run command
    typer.echo(f"Would run quick job for: {subject}")
    typer.echo("Please use 'xsarena run book' with appropriate parameters instead.")
