from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
import yaml

from ..core.jobs2_runner import JobRunner
from ..core.prompt import compose_prompt
from ..core.recipes import recipe_from_mixer

app = typer.Typer(help="Fast headless run with standardized parameters")


def _slugify(s: str) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "book"


@app.command("start")
def fast_start(
    subject: str = typer.Argument(..., help='Book subject, e.g., "Contract Law — E&W"'),
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
    backend: str = typer.Option(
        "bridge", "--backend", "-B", help="Backend to use (bridge or openrouter)"
    ),
):
    """DEPRECATED: Use 'xsarena run book' instead."""
    typer.echo("⚠️  DEPRECATED: Use 'xsarena run book' with appropriate profile instead.")
    
    # Map fast parameters to run command
    # For now, we'll just show a message since the run command doesn't have all the same parameters
    typer.echo(f"Would run fast job for: {subject}")
    typer.echo("Please use 'xsarena run book' with appropriate parameters instead.")
