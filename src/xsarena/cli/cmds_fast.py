from __future__ import annotations
from pathlib import Path
from typing import Optional
import os
import yaml

import typer

from .context import CLIContext
from ..core.prompt import compose_prompt
from ..core.recipes import recipe_from_mixer
from ..core.jobs2_runner import JobRunner

app = typer.Typer(help="Fast headless run with standardized parameters")

def _slugify(s: str) -> str:
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "book"

@app.command("start")
def fast_start(
    subject: str = typer.Argument(..., help='Book subject, e.g., "Contract Law — E&W"'),
    base: str = typer.Option("zero2hero", "--base", "-b", help="Base mode", case_sensitive=False),
    no_bs: bool = typer.Option(True, "--no-bs/--no-no-bs", help="Plain, no fluff"),
    narrative: bool = typer.Option(False, "--narrative/--no-narrative", help="Teach-before-use narrative"),
    compressed: bool = typer.Option(True, "--compressed/--no-compressed", help="Compressed narrative overlay"),
    bilingual: bool = typer.Option(False, "--bilingual/--no-bilingual", help="Bilingual hint overlay (pairs)"),
    out_path: Optional[str] = typer.Option(None, "--out", "-o", help="Output file path"),
    max_chunks: int = typer.Option(12, "--max", help="Max chunks"),
    min_chars: int = typer.Option(4200, "--min", help="Min chars per chunk"),
    passes: int = typer.Option(1, "--passes", help="Auto-extend passes per chunk (0..3)"),
    backend: str = typer.Option("bridge", "--backend", "-B", help="Backend to use (bridge or openrouter)"),
):
    """DEPRECATED: Use 'xsarena run book' instead."""
    typer.echo("⚠️  DEPRECATED: Use 'xsarena run book' instead.")
    
    base = base.lower()
    overlays = []
    if no_bs: overlays.append("no_bs")
    if narrative: overlays.append("narrative")
    if compressed: overlays.append("compressed")
    if bilingual: overlays.append("bilingual")

    extra_note = "Explain doctrine by what it lets actors do and forbids; name the trade-offs." if "law" in subject.lower() else ""

    composition = compose_prompt(
        subject=subject, base=base, overlays=overlays, extra_notes=extra_note, min_chars=min_chars, passes=passes, max_chunks=max_chunks
    )
    final_system = composition.system_text

    if not out_path:
        out_path = f"./books/{_slugify(subject)}.final.md"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    task_map = {"zero2hero": "book.zero2hero", "reference": "book.reference", "pop": "book.pop", "nobs": "book.nobs"}
    task = task_map.get(base, "book.zero2hero")

    rec = recipe_from_mixer(subject, task, final_system, out_path, min_chars, passes, max_chunks)

    # write recipe for audit
    recipes = Path("recipes"); recipes.mkdir(exist_ok=True)
    rp = recipes / f"fast_{_slugify(subject)}.yml"
    with open(rp, "w", encoding="utf-8") as f:
        yaml.safe_dump(rec, f, sort_keys=False, allow_unicode=True)
    typer.echo(f"[fast] Recipe saved → {rp}")

    # run using the canonical run path
    import os
    os.environ["XSA_BACKEND"] = backend
    runner = JobRunner({})
    job_id = runner.submit(playbook={"name": f"Fast run: {subject}", **rec}, params={"max_chunks": rec["max_chunks"], "continuation": rec["continuation"], "io": rec["io"]})
    runner.run_job(job_id)
    typer.echo(f"[fast] Run complete. job_id={job_id}")
    typer.echo(f"[fast] Output → {out_path}")