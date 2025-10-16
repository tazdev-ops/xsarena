from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer

from ..core.jobs2_runner import JobRunner
from ..core.prompt import compose_prompt
from ..core.recipes import recipe_from_mixer

app = typer.Typer(help="Mode mixer: compose presets → recipe → run")

BASE_CHOICES = ["zero2hero", "reference", "pop", "nobs"]


def _slugify(s: str) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "book"


def _write_preview(subject: str, text: str) -> Path:
    outdir = Path("directives") / "_mixer"
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / f"{_slugify(subject)}.prompt.md"
    p.write_text(text, encoding="utf-8")
    return p


def _write_recipe_file(subject: str, recipe: dict) -> Path:
    recipes = Path("recipes")
    recipes.mkdir(parents=True, exist_ok=True)
    rp = recipes / f"mixer_{_slugify(subject)}.yml"
    import yaml

    with open(rp, "w", encoding="utf-8") as f:
        yaml.safe_dump(recipe, f, sort_keys=False, allow_unicode=True)
    return rp


@app.command("start")
def mix_start(
    subject: str = typer.Argument(
        ..., help='Book subject, e.g., "Contract Law — England & Wales"'
    ),
    base: str = typer.Option(
        "zero2hero", "--base", "-b", help="Base mode", case_sensitive=False
    ),
    no_bs: bool = typer.Option(True, "--no-bs/--no-no-bs", help="Plain, no fluff"),
    narrative: bool = typer.Option(
        False, "--narrative/--no-narrative", help="Teach-before-use narrative"
    ),
    compressed: bool = typer.Option(
        True, "--compressed/--no-compressed", help="Compressed narrative overlay"
    ),
    bilingual: bool = typer.Option(
        False, "--bilingual/--no-bilingual", help="Bilingual hint overlay (pairs)"
    ),
    out_path: Optional[str] = typer.Option(
        None, "--out", "-o", help="Output file path"
    ),
    max_chunks: int = typer.Option(12, "--max", help="Max chunks"),
    min_chars: int = typer.Option(4200, "--min", help="Min chars per chunk"),
    passes: int = typer.Option(
        1, "--passes", help="Auto-extend passes per chunk (0..3)"
    ),
    edit: bool = typer.Option(
        True, "--edit/--no-edit", help="Open prompt in $EDITOR before running"
    ),
    dry: bool = typer.Option(
        False, "--dry", help="Do not run; only write preview + recipe"
    ),
):
    """DEPRECATED: Use 'xsarena run book' instead."""
    typer.echo("⚠️  DEPRECATED: Use 'xsarena run book' instead.")
    
    # Map mixer parameters to run command
    typer.echo(f"Would run mixer job for: {subject}")
    typer.echo("Please use 'xsarena run book' with appropriate parameters instead.")
