from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import typer

from .context import CLIContext
from ..core.prompt import compose_prompt
from ..core.jobs2_runner import JobRunner
from ..core.recipes import recipe_from_mixer
from ..core.specs import LENGTH_PRESETS, SPAN_PRESETS, DEFAULT_PROFILES

app = typer.Typer(help="Quick launcher: wait for capture, then run a long, dense book with curated profiles")

def _slugify(s: str) -> str:
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "book"

@app.command("start")
def quick_start(
    ctx: typer.Context,
    subject: str = typer.Argument(..., help="Book subject"),
    profile: str = typer.Option("", "--profile", help="Preset: clinical-masters|elections-focus|compressed-handbook|pop-explainer|bilingual-pairs"),
    length: str = typer.Option("long", "--length", help="Per-message length: standard|long|very-long|max"),
    span: str = typer.Option("book", "--span", help="Total span: medium|long|book"),
    out_path: str = typer.Option("", "--out", "-o", help="Output path (defaults to books/finals/<slug>.final.md)"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Prompt to wait for browser capture before starting"),
    extra_file: List[str] = typer.Option([], "--extra-file", "-E", help="Append file(s) to system prompt (e.g., directives/_rules/rules.merged.md)")
):
    cli: CLIContext = ctx.obj

    # Resolve presets
    L = LENGTH_PRESETS.get(length.lower())
    if not L:
        typer.echo("Unknown --length. Choose: standard|long|very-long|max")
        raise typer.Exit(2)
    total_chunks = SPAN_PRESETS.get(span.lower())
    if not total_chunks:
        typer.echo("Unknown --span. Choose: medium|long|book")
        raise typer.Exit(2)

    overlays = ["narrative", "no_bs"]  # default: narrative not compressed
    extra_note = ""
    if profile:
        spec = DEFAULT_PROFILES.get(profile)
        if not spec:
            typer.echo(f"Unknown profile: {profile}")
            raise typer.Exit(2)
        overlays = spec["overlays"]
        extra_note = spec["extra"]

    comp = compose_prompt(subject=subject, base="zero2hero", overlays=overlays, extra_notes=extra_note,
                          min_chars=L["min"], passes=L["passes"], max_chunks=total_chunks)
    system_text = comp.system_text
    for ef in extra_file:
        ep = Path(ef)
        if ep.exists() and ep.is_file():
            try:
                system_text += "\n\n" + ep.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    # Output
    if not out_path:
        out_path = f"./books/finals/{_slugify(subject)}.final.md"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # Wait for capture (bridge)
    if wait:
        typer.echo("\nOpen https://lmarena.ai and add '#bridge=8080' (or your port) to the URL.")
        typer.echo("Click 'Retry' on any message to activate the tab.")
        typer.echo("Press ENTER here to begin...")
        try:
            input()
        except KeyboardInterrupt:
            raise typer.Exit(1)

    # Build recipe + run
    task = "book.zero2hero"
    rec = {
        "task": task,
        "subject": subject,
        "system_text": system_text,
        "max_chunks": total_chunks,
        "continuation": {"mode": "anchor", "minChars": L["min"], "pushPasses": L["passes"], "repeatWarn": True},
        "io": {"output": "file", "outPath": out_path},
    }
    runner = JobRunner({})
    job_id = runner.submit(playbook={"name": f"Quick run: {subject}", **rec}, params={"max_chunks": rec["max_chunks"], "continuation": rec["continuation"], "io": rec["io"]})
    typer.echo(f"[quick] submitted: {job_id}")
    runner.run_job(job_id)
    typer.echo(f"[quick] done → {out_path}")