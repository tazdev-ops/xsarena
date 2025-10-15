from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional

import typer

from .context import CLIContext
from ..core.prompt import compose_prompt
from ..core.recipes import recipe_from_mixer
from ..core.jobs2_runner import JobRunner

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
    subject: str = typer.Argument(..., help='Book subject, e.g., "Contract Law — England & Wales"'),
    base: str = typer.Option("zero2hero", "--base", "-b", help="Base mode", case_sensitive=False),
    no_bs: bool = typer.Option(True, "--no-bs/--no-no-bs", help="Plain, no fluff"),
    narrative: bool = typer.Option(False, "--narrative/--no-narrative", help="Teach-before-use narrative"),
    compressed: bool = typer.Option(True, "--compressed/--no-compressed", help="Compressed narrative overlay"),
    bilingual: bool = typer.Option(False, "--bilingual/--no-bilingual", help="Bilingual hint overlay (pairs)"),
    out_path: Optional[str] = typer.Option(None, "--out", "-o", help="Output file path"),
    max_chunks: int = typer.Option(12, "--max", help="Max chunks"),
    min_chars: int = typer.Option(4200, "--min", help="Min chars per chunk"),
    passes: int = typer.Option(1, "--passes", help="Auto-extend passes per chunk (0..3)"),
    edit: bool = typer.Option(True, "--edit/--no-edit", help="Open prompt in $EDITOR before running"),
    dry: bool = typer.Option(False, "--dry", help="Do not run; only write preview + recipe"),
):
    base = base.lower()
    if base not in BASE_CHOICES:
        typer.echo(f"Unknown base: {base}. Choose from: {', '.join(BASE_CHOICES)}")
        raise typer.Exit(2)

    chosen_keys: List[str] = []
    if no_bs: chosen_keys.append("no_bs")
    if narrative: chosen_keys.append("narrative")
    if compressed: chosen_keys.append("compressed")
    if bilingual: chosen_keys.append("bilingual")

    extra_note = ""
    if "law" in subject.lower():
        extra_note = "Explain doctrine by what it lets actors do and forbids; name the trade-offs."

    composition = compose_prompt(
        subject=subject,
        base=base,
        overlays=chosen_keys,
        extra_notes=extra_note,
        min_chars=min_chars,
        passes=passes,
        max_chunks=max_chunks
    )
    if composition.warnings:
        typer.echo("Warnings:")
        for w in composition.warnings:
            typer.echo(f"  - {w}")

    final_system = composition.system_text
    if edit:
        edited = typer.edit(final_system)
        if edited:
            final_system = edited.strip()

    pv_path = _write_preview(subject, final_system)
    typer.echo(f"[mixer] Prompt preview saved → {pv_path}")

    if not out_path:
        out_path = f"./books/{_slugify(subject)}.final.md"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # map base to task
    task_map = {"zero2hero": "book.zero2hero", "reference": "book.reference", "pop": "book.pop", "nobs": "book.nobs"}
    task = task_map.get(base, "book.zero2hero")

    rec = recipe_from_mixer(subject, task, final_system, out_path, min_chars, passes, max_chunks)
    rp = _write_recipe_file(subject, rec)
    typer.echo(f"[mixer] Recipe written → {rp}")

    if dry:
        typer.echo("[mixer] Dry-run: not starting job.")
        return

    runner = JobRunner({})
    job_id = runner.submit(playbook={"name": f"Mixer run: {subject}", **rec}, params={"max_chunks": rec["max_chunks"], "continuation": rec["continuation"], "io": rec["io"]})
    runner.run_job(job_id)
    typer.echo(f"[mixer] Run complete. job_id={job_id}")