from __future__ import annotations
from pathlib import Path
from typing import Optional, List
import asyncio
import typer
import yaml

from .context import CLIContext
from ..core.specs import RunSpec, LENGTH_PRESETS, SPAN_PRESETS
from ..core.orchestrator import build_system_text, build_recipe, seed_continue
from ..core.jobs2_runner import JobRunner
from ..core.profiles import load_profiles

app = typer.Typer(help="Unified runner: compose/plan/continue with descriptive presets.")

@app.command("book")
def run_book(
    ctx: typer.Context,
    subject: str = typer.Argument(...),
    profile: str = typer.Option("", "--profile"),
    length: str = typer.Option("long", "--length", help="standard|long|very-long|max"),
    span: str = typer.Option("book", "--span", help="medium|long|book"),
    extra_file: List[str] = typer.Option([], "--extra-file", "-E"),
    out_path: Optional[str] = typer.Option(None, "--out", "-o"),
    wait: bool = typer.Option(True, "--wait/--no-wait")
):
    cli: CLIContext = ctx.obj
    # presets
    if length not in LENGTH_PRESETS: raise typer.Exit(2)
    if span not in SPAN_PRESETS: raise typer.Exit(2)
    overlays = ["narrative", "no_bs"]; extra_note = ""
    if profile:
        prof = load_profiles().get(profile)
        if not prof: raise typer.Exit(2)
        overlays = prof["overlays"]; extra_note = prof["extra"]

    spec = RunSpec(subject=subject, length=length, span=span, overlays=overlays, extra_note=extra_note, extra_files=list(extra_file), out_path=out_path)
    system = build_system_text(spec)
    recipe = build_recipe(spec, system)

    if wait:
        typer.echo("\nOpen https://lmarena.ai and add '#bridge=8080'. Click Retry, then press ENTER.")
        try: input()
        except KeyboardInterrupt: raise typer.Exit(1)

    runner = JobRunner({})
    job_id = runner.submit(playbook={"name": f"Run: {subject}", **recipe}, params={"max_chunks": recipe["max_chunks"], "continuation": recipe["continuation"], "io": recipe["io"]})
    typer.echo(f"[run] submitted: {job_id}")
    runner.run_job(job_id)
    typer.echo(f"[run] done → {recipe['io']['outPath']}")

@app.command("continue")
def run_continue(
    ctx: typer.Context,
    book_file: str = typer.Argument(...),
    subject: Optional[str] = typer.Option(None, "--subject", "-s"),
    profile: str = typer.Option("", "--profile"),
    length: str = typer.Option("long", "--length", help="standard|long|very-long|max"),
    span: str = typer.Option("book", "--span", help="medium|long|book"),
    until_end: bool = typer.Option(False, "--until-end"),
    extra_file: List[str] = typer.Option([], "--extra-file", "-E"),
    wait: bool = typer.Option(True, "--wait/--no-wait")
):
    cli: CLIContext = typer.get_current_context().obj
    p = Path(book_file)
    if not p.exists(): raise typer.Exit(1)
    # defaults
    if length not in LENGTH_PRESETS: raise typer.Exit(2)
    if span not in SPAN_PRESETS: raise typer.Exit(2)
    target_subject = subject or p.stem.replace(".final","").replace(".manual.en","").replace(".outline","").replace("_"," ").replace("-"," ").strip().title() or "Subject"

    overlays = ["narrative", "no_bs"]; extra_note = ""
    if profile:
        prof = load_profiles().get(profile)
        if not prof: raise typer.Exit(2)
        overlays = prof["overlays"]; extra_note = prof["extra"]

    spec = RunSpec(subject=target_subject, length=length, span=span, overlays=overlays, extra_note=extra_note, extra_files=list(extra_file))
    min_chars, passes, chunks = spec.resolved()
    system = build_system_text(spec)

    if wait:
        typer.echo("\nOpen https://lmarena.ai and add '#bridge=8080'. Click Retry, then press ENTER.")
        try: input()
        except KeyboardInterrupt: raise typer.Exit(1)

    asyncio.run(seed_continue(cli.engine, p, system, min_chars, passes, None if until_end else chunks))
    typer.echo(f"[run/continue] done → {p}")