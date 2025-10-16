from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import List, Optional

import typer
import yaml

from ..core.orchestrator import (
    build_system_text,
    seed_continue,
)  # Import from the old orchestrator.py file
from ..core.profiles import load_profiles
from ..core.specs import DEFAULT_PROFILES, LENGTH_PRESETS, SPAN_PRESETS, RunSpec
from ..core.v2_orchestrator.orchestrator import Orchestrator
from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset
from .context import CLIContext

app = typer.Typer(
    help="Unified runner: compose/plan/continue with descriptive presets."
)


@app.command("book")
def run_book(
    ctx: typer.Context,
    subject: str = typer.Argument(...),
    profile: str = typer.Option("", "--profile"),
    length: str = typer.Option("long", "--length", help="standard|long|very-long|max"),
    span: str = typer.Option("book", "--span", help="medium|long|book"),
    extra_file: List[str] = typer.Option([], "--extra-file", "-E"),
    out_path: Optional[str] = typer.Option(None, "--out", "-o"),
    wait: bool = typer.Option(True, "--wait/--no-wait"),
):
    cli: CLIContext = ctx.obj
    # presets
    if length not in LENGTH_PRESETS:
        raise typer.Exit(2)
    if span not in SPAN_PRESETS:
        raise typer.Exit(2)
    overlays = ["narrative", "no_bs"]
    extra_note = ""
    if profile:
        prof = load_profiles().get(profile)
        if not prof:
            raise typer.Exit(2)
        overlays = prof["overlays"]
        extra_note = prof["extra"]

    # Create the new RunSpecV2 and use the new orchestrator system
    length_preset = LengthPreset(length)
    span_preset = SpanPreset(span)

    run_spec = RunSpecV2(
        subject=subject,
        length=length_preset,
        span=span_preset,
        overlays=overlays,
        extra_note=extra_note,
        extra_files=list(extra_file),
        out_path=out_path,
        profile=profile,
    )

    # Use the new orchestrator system
    orchestrator = Orchestrator()

    if wait:
        typer.echo(
            "\nOpen https://lmarena.ai and add '#bridge=8080'. Click Retry, then press ENTER."
        )
        try:
            input()
        except KeyboardInterrupt:
            raise typer.Exit(1)

    # Submit job using the new system
    import warnings

    warnings.warn("Using new JobsV3 system", DeprecationWarning)

    # Run the job using the orchestrator
    job_id = asyncio.run(orchestrator.run_spec(run_spec, backend_type="bridge"))

    typer.echo(f"[run] submitted: {job_id}")
    typer.echo(
        f"[run] done → {out_path or f'./books/{subject.replace(' ', '_')}.final.md'}"
    )


@app.command("from-recipe")
def run_from_recipe(
    file: str = typer.Argument(..., help="Recipe file (.yml/.yaml/.json)"),
    apply: bool = typer.Option(True, "--apply/--dry-run", help="Execute job (default: execute)"),
):
    """Run a job from recipe file (replaces 'jobs run')."""
    if not os.path.exists(file):
        typer.echo(f"Recipe not found: {file}")
        raise typer.Exit(1)
    
    # Load recipe file
    with open(file, "r", encoding="utf-8") as f:
        if file.endswith((".yml", ".yaml")):
            data = yaml.safe_load(f) or {}
        else:
            data = json.load(f)

    if not apply:
        typer.echo(f"Would run: {file}")
        typer.echo("Use --apply to execute.")
        return

    subject = data.get("subject") or "book"
    task = data.get("task") or "book.zero2hero"
    system_text = data.get("system_text") or ""
    io = data.get("io") or {}
    out_path = io.get("outPath") or io.get("out") or f"./books/{subject}.final.md"
    cont = data.get("continuation") or {}
    max_chunks = int(data.get("max_chunks") or 8)
    prelude = data.get("prelude", [])

    # Use the new orchestrator system
    orchestrator = Orchestrator()

    # Create RunSpecV2 equivalent
    run_spec = RunSpecV2(
        subject=subject,
        length=LengthPreset("long"),  # Use default length preset
        span=SpanPreset("book"),      # Use default span preset
        overlays=["narrative", "no_bs"],  # Default overlays
        extra_note="",
        extra_files=[],
        out_path=out_path,
        profile="",
    )

    # Submit job using the new system
    import warnings
    warnings.warn("Using new JobsV3 system", DeprecationWarning)

    # Run the job using the orchestrator
    job_id = asyncio.run(orchestrator.run_spec(run_spec, backend_type="bridge"))

    typer.echo(f"[run] submitted: {job_id}")
    typer.echo(f"[run] done: {job_id}")
    typer.echo(f"[run] final → {out_path}")


@app.command("from-plan")
def run_from_plan(
    ctx: typer.Context,
    subject: Optional[str] = typer.Option(
        None, "--subject", "-s", help="Final subject/title (leave empty to infer)"
    ),
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
    extra_file: List[str] = typer.Option(
        [],
        "--extra-file",
        "-E",
        help="Append file(s) to system prompt (e.g., directives/_rules/rules.merged.md)",
    ),
    wait: bool = typer.Option(
        True,
        "--wait/--no-wait",
        help="Prompt to wait for browser capture before starting",
    ),
):
    """
    Plan from rough seeds in your editor, then run a long, dense book.
    Replaces 'plan start' command.
    """
    cli: CLIContext = ctx.obj

    _PLANNER_PROMPT = """You are an editorial planner for a long-form self-study manual.
The user will provide rough seeds (topics/notes). Your job:
- subject: one-line final title (concise, specific)
- goal: 3–5 sentences (scope, depth, audience, exclusions)
- focus: 5–8 bullets (what to emphasize/avoid)
- outline: 10–16 top-level sections; each item has:
    - title: short section heading
    - cover: 2–4 bullets of what to cover
Return STRICT YAML only with keys: subject, goal, focus, outline. No code fences, no commentary.

Seeds:
<<<SEEDS
{seeds}
SEEDS>>>"""

    def _editor_seed() -> str:
        return (
            "# Write your rough seeds below. One item per line; keep it messy. Save and close to proceed.\n"
            "# Example:\n"
            "# 1) cicero (speeches)\n"
            "# 2) roman republic history (1st BCE)\n"
            "# 3) political history (theories for understanding)\n"
            "# 4) relevant social sciences lenses\n"
            "# 5) roman law/constitution (relevant bits)\n\n"
        )

    # Open editor for seeds
    seeds = typer.edit(_editor_seed())
    if not seeds or not seeds.strip():
        typer.echo("No seeds provided. Aborting.")
        raise typer.Exit(2)

    # Resolve descriptive presets
    L = LENGTH_PRESETS.get(length.lower())
    if not L:
        typer.echo("Unknown --length. Choose: standard|long|very-long|max")
        raise typer.Exit(2)
    total_chunks = SPAN_PRESETS.get(span.lower())
    if not total_chunks:
        typer.echo("Unknown --span. Choose: medium|long|book")
        raise typer.Exit(2)

    overlays = ["narrative", "no_bs"]  # default: narrative (not compressed)
    extra_note = ""
    if profile:
        spec = DEFAULT_PROFILES.get(profile)
        if not spec:
            typer.echo(f"Unknown profile: {profile}")
            raise typer.Exit(2)
        overlays = spec["overlays"]
        extra_note = spec["extra"]

    # Ask AI to plan in YAML
    async def _plan():
        return await cli.engine.send_and_collect(
            _PLANNER_PROMPT.format(seeds=seeds), system_prompt=None
        )

    yaml_text = asyncio.run(_plan())

    # Parse YAML; fallbacks if needed
    plan = {}
    try:
        plan = yaml.safe_load(yaml_text) or {}
    except Exception:
        plan = {}
    plan_subject = (plan.get("subject") or subject or "Untitled Project").strip()

    # Compose system text using overlays + optional extra note
    from ..core.prompt import compose_prompt
    comp = compose_prompt(
        subject=plan_subject,
        base="zero2hero",
        overlays=overlays,
        extra_notes=extra_note,
        min_chars=L["min"],
        passes=L["passes"],
        max_chunks=total_chunks,
    )
    system_text = comp.system_text

    # Inject outline-first scaffold if we got an outline
    if isinstance(plan.get("outline"), list) and plan["outline"]:
        # Format outline as a readable scaffold
        try:
            import textwrap

            outline_lines = []
            for idx, sec in enumerate(plan["outline"], 1):
                title = (sec.get("title") or f"Section {idx}").strip()
                cover = sec.get("cover") or []
                outline_lines.append(f"- {idx}. {title}")
                for b in cover:
                    outline_lines.append(f"    • {b}")
            scaffold = "\n".join(outline_lines)
            system_text += (
                "\n\nOUTLINE-FIRST SCAFFOLD\n"
                "- First chunk: produce a chapter-by-chapter outline consistent with this planner output; end with NEXT: [Begin Chapter 1].\n"
                "- Subsequent chunks: follow the outline; narrative prose; define terms once; no bullet walls.\n"
                "PLANNER OUTLINE (guidance):\n" + textwrap.dedent(scaffold)
            )
        except Exception:
            pass

    # Append extra files (rules, domain sheets)
    for ef in extra_file:
        ep = Path(ef)
        if ep.exists() and ep.is_file():
            try:
                system_text += "\n\n" + ep.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    # Output path
    if not out_path:
        out_path = f"./books/finals/{_slugify(plan_subject)}.final.md"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # Optional wait for capture
    if wait:
        typer.echo(
            "\nOpen https://lmarena.ai and add '#bridge=8080' (or your port) to the URL."
        )
        typer.echo("Click 'Retry' on any message to activate the tab.")
        typer.echo("Press ENTER here to begin...")
        try:
            input()
        except KeyboardInterrupt:
            raise typer.Exit(1)

    # Use the new orchestrator system
    orchestrator = Orchestrator()

    # Create RunSpecV2 with the planned system text
    run_spec = RunSpecV2(
        subject=plan_subject,
        length=LengthPreset(length),
        span=SpanPreset(span),
        overlays=overlays,
        extra_note=extra_note,
        extra_files=list(extra_file),
        out_path=out_path,
        profile=profile,
    )

    # Submit job using the new system
    import warnings
    warnings.warn("Using new JobsV3 system", DeprecationWarning)

    # Run the job using the orchestrator
    job_id = asyncio.run(orchestrator.run_spec(run_spec, backend_type="bridge"))

    typer.echo(f"[run] submitted: {job_id}")
    typer.echo(f"[run] done → {out_path}")


def _slugify(s: str) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "book"


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
    wait: bool = typer.Option(True, "--wait/--no-wait"),
):
    cli: CLIContext = ctx.obj
    p = Path(book_file)
    if not p.exists():
        raise typer.Exit(1)
    # defaults
    if length not in LENGTH_PRESETS:
        raise typer.Exit(2)
    if span not in SPAN_PRESETS:
        raise typer.Exit(2)
    target_subject = (
        subject
        or p.stem.replace(".final", "")
        .replace(".manual.en", "")
        .replace(".outline", "")
        .replace("_", " ")
        .replace("-", " ")
        .strip()
        .title()
        or "Subject"
    )

    overlays = ["narrative", "no_bs"]
    extra_note = ""
    if profile:
        prof = load_profiles().get(profile)
        if not prof:
            raise typer.Exit(2)
        overlays = prof["overlays"]
        extra_note = prof["extra"]

    # Use the new orchestrator system
    orchestrator = Orchestrator()

    # Create RunSpecV2 for continue operation
    run_spec = RunSpecV2(
        subject=target_subject,
        length=LengthPreset(length),
        span=SpanPreset(span),
        overlays=overlays,
        extra_note=extra_note,
        extra_files=list(extra_file),
        out_path=str(p),
        profile=profile,
    )

    if wait:
        typer.echo(
            "\nOpen https://lmarena.ai and add '#bridge=8080'. Click Retry, then press ENTER."
        )
        try:
            input()
        except KeyboardInterrupt:
            raise typer.Exit(1)

    # Use the orchestrator to continue from file
    job_id = asyncio.run(orchestrator.run_continue(run_spec, str(p), until_end=until_end))
    
    typer.echo(f"[run] submitted: {job_id}")
    typer.echo(f"[run/continue] done → {p}")
