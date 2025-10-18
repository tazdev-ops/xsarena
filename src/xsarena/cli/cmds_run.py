from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
from pathlib import Path
from typing import List, Optional

import typer
import yaml

from ..core.profiles import load_profiles
from ..core.prompt import compose_prompt
from ..core.specs import DEFAULT_PROFILES, LENGTH_PRESETS, SPAN_PRESETS
from ..core.state import SessionState
from ..core.v2_orchestrator.orchestrator import Orchestrator
from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset
from ..utils.directives import find_directive
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
    plan: bool = typer.Option(False, "--plan", help="Generate an outline first."),
    window: int = typer.Option(
        None, "--window", help="Set history window size for this run."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show the composed prompt/spec without running jobs"
    ),
    endpoint: str = typer.Option(
        None, "--endpoint", help="Use settings from endpoints.yml"
    ),
    priority: int = typer.Option(
        5, "--priority", help="Job priority (0=lowest, 5=default, 10=highest)"
    ),
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
):
    # Load endpoint settings if specified
    endpoint_config = {}
    if endpoint:
        endpoints_path = Path("endpoints.yml")
        if not endpoints_path.exists():
            typer.echo("Error: endpoints.yml file not found")
            raise typer.Exit(1)

        try:
            with open(endpoints_path, "r", encoding="utf-8") as f:
                endpoints_data = yaml.safe_load(f) or {}

            if endpoint not in endpoints_data:
                typer.echo(f"Error: endpoint '{endpoint}' not found in endpoints.yml")
                raise typer.Exit(1)

            endpoint_config = endpoints_data[endpoint]
        except Exception as e:
            typer.echo(f"Error loading endpoints.yml: {e}")
            raise typer.Exit(1)

    # Apply endpoint settings if available, otherwise use defaults
    overlays = endpoint_config.get("overlays", ["narrative", "no_bs"])
    extra_note = endpoint_config.get("extra", "")

    # Override CLI options with endpoint values if not explicitly set via CLI
    length = endpoint_config.get("length", length)
    span = endpoint_config.get("span", span)
    extra_file = endpoint_config.get("extra_files", list(extra_file))
    out_path = endpoint_config.get("out_path", out_path)

    # Get bridge-specific IDs from endpoint config
    endpoint_bridge_session_id = endpoint_config.get("bridge_session_id")
    endpoint_bridge_message_id = endpoint_config.get("bridge_message_id")

    # presets
    if length not in LENGTH_PRESETS:
        raise typer.Exit(2)
    if span not in SPAN_PRESETS:
        raise typer.Exit(2)

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
        generate_plan=plan,
        window_size=window,
        bridge_session_id=endpoint_bridge_session_id,
        bridge_message_id=endpoint_bridge_message_id,
    )

    # Use the new orchestrator system
    orchestrator = Orchestrator()

    # Compose the system_text to use for dry-run or actual run
    session_state = SessionState.load_from_file(".xsarena/session_state.json")
    resolved = run_spec.resolved()
    resolved["min_length"] = getattr(
        session_state, "output_min_chars", resolved["min_length"]
    )

    # compose system_text here as you already do:
    comp = compose_prompt(
        subject=run_spec.subject,
        base="zero2hero",
        overlays=run_spec.overlays,
        extra_notes=run_spec.extra_note,
        min_chars=resolved["min_length"],
        passes=resolved["passes"],
        max_chunks=resolved["chunks"],
        apply_reading_overlay=getattr(session_state, "reading_overlay_on", False),
    )
    system_text = comp.system_text
    for file_path in run_spec.extra_files:
        p = Path(file_path)
        if p.exists():
            system_text += "\n\n" + p.read_text(encoding="utf-8", errors="ignore")

    # If dry-run is enabled, show the spec and system_text and exit
    if dry_run:
        typer.echo("[DRY RUN] Would run with the following configuration:")
        typer.echo("=" * 50)
        typer.echo("Run Specification:")
        typer.echo(f"  Subject: {run_spec.subject}")
        typer.echo(f"  Length: {run_spec.length}")
        typer.echo(f"  Span: {run_spec.span}")
        typer.echo(f"  Overlays: {run_spec.overlays}")
        typer.echo(f"  Extra Note: {run_spec.extra_note}")
        typer.echo(f"  Extra Files: {run_spec.extra_files}")
        typer.echo(f"  Profile: {run_spec.profile}")
        typer.echo(f"  Out Path: {run_spec.out_path}")
        typer.echo(f"  Generate Plan: {run_spec.generate_plan}")
        typer.echo(f"  Window Size: {run_spec.window_size}")
        typer.echo("-" * 50)
        typer.echo("System Text:")
        typer.echo(system_text)
        typer.echo("=" * 50)
        typer.echo("[DRY RUN] Execution completed (no actual job submitted)")
        return

    if wait:
        typer.echo(
            "\nOpen https://lmarena.ai and add '#bridge=5102'. Click Retry, then press ENTER."
        )
        try:
            input()
        except KeyboardInterrupt:
            raise typer.Exit(1)

    # Submit job using the new system
    import warnings

    warnings.warn("Using new JobsV3 system", DeprecationWarning, stacklevel=2)

    # Run the job using the orchestrator
    job_id = asyncio.run(
        orchestrator.run_spec(run_spec, backend_type="bridge", priority=priority)
    )

    typer.echo(f"[run] submitted: {job_id}")

    if follow:
        # Follow the job to completion
        from ..core.jobs.model import JobManager

        job_runner = JobManager()
        asyncio.run(job_runner.wait_for_job_completion(job_id))
        typer.echo(
            f"[run] done → {out_path or f'./books/{subject.replace(' ', '_')}.final.md'}"
        )
    else:
        typer.echo(
            f"[run] done → {out_path or f'./books/{subject.replace(' ', '_')}.final.md'}"
        )


@app.command("from-recipe")
def run_from_recipe(
    file: str = typer.Argument(..., help="Recipe file (.yml/.yaml/.json)"),
    apply: bool = typer.Option(
        True, "--apply/--dry-run", help="Execute job (default: execute)"
    ),
):
    """Run a job from recipe file (replaces 'jobs run')."""
    if not os.path.exists(file):
        typer.echo(f"Recipe not found: {file}")
        raise typer.Exit(1)

    # Load recipe file
    with open(file, "r", encoding="utf-8") as f:
        data = (
            yaml.safe_load(f) or {}
            if file.endswith((".yml", ".yaml"))
            else json.load(f)
        )

    subject = data.get("subject") or "book"

    # Get overlays, length, and span from recipe data, with defaults
    overlays = data.get("overlays", ["narrative", "no_bs"])
    length = data.get("length", "long")
    span = data.get("span", "book")

    # Get base from recipe, default to "zero2hero"
    base = data.get("base", "zero2hero")

    if not apply:
        # For dry run, show the spec and system_text
        from ..core.prompt import compose_prompt
        from ..core.state import SessionState
        from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset

        # Create RunSpecV2 with values from recipe for display
        run_spec = RunSpecV2(
            subject=subject,
            length=LengthPreset(length),
            span=SpanPreset(span),
            overlays=overlays,
            extra_note="",
            extra_files=[],
            out_path="",
            profile="",
        )

        # Compose the system_text to show
        session_state = SessionState.load_from_file(".xsarena/session_state.json")
        resolved = run_spec.resolved()
        resolved["min_length"] = getattr(
            session_state, "output_min_chars", resolved["min_length"]
        )

        # compose system_text here as you already do:
        comp = compose_prompt(
            subject=run_spec.subject,
            base=base,
            overlays=run_spec.overlays,
            extra_notes=run_spec.extra_note,
            min_chars=resolved["min_length"],
            passes=resolved["passes"],
            max_chunks=resolved["chunks"],
            apply_reading_overlay=getattr(session_state, "reading_overlay_on", False),
        )
        system_text = comp.system_text
        for file_path in run_spec.extra_files:
            p = Path(file_path)
            if p.exists():
                system_text += "\n\n" + p.read_text(encoding="utf-8", errors="ignore")

        typer.echo("[DRY RUN] Would run with the following configuration:")
        typer.echo("=" * 50)
        typer.echo("Run Specification:")
        typer.echo(f"  Subject: {run_spec.subject}")
        typer.echo(f"  Length: {run_spec.length}")
        typer.echo(f"  Span: {run_spec.span}")
        typer.echo(f"  Overlays: {run_spec.overlays}")
        typer.echo(f"  Extra Note: {run_spec.extra_note}")
        typer.echo(f"  Extra Files: {run_spec.extra_files}")
        typer.echo(f"  Profile: {run_spec.profile}")
        typer.echo("-" * 50)
        typer.echo("System Text:")
        typer.echo(system_text)
        typer.echo("=" * 50)
        typer.echo("[DRY RUN] Execution completed (no actual job submitted)")
        return

    data.get("task") or "book.zero2hero"
    data.get("system_text") or ""
    io = data.get("io") or {}

    if not (io.get("outPath") or io.get("out")):
        slug = _slugify(subject)
        out_path = f"./books/{slug}.final.md"
    else:
        out_path = io.get("outPath") or io.get("out")

    # Create parent directories if they don't exist
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    data.get("continuation") or {}
    int(data.get("max_chunks") or 8)
    data.get("prelude", [])

    # Use the new orchestrator system
    orchestrator = Orchestrator()

    # Create RunSpecV2 with values from recipe
    run_spec = RunSpecV2(
        subject=subject,
        length=LengthPreset(length),
        span=SpanPreset(span),
        overlays=overlays,
        extra_note="",
        extra_files=[],
        out_path=out_path,
        profile="",
    )

    # Submit job using the new system
    import warnings

    warnings.warn("Using new JobsV3 system", DeprecationWarning, stacklevel=2)

    # Run the job using the orchestrator
    job_id = asyncio.run(orchestrator.run_spec(run_spec, backend_type="bridge"))

    typer.echo(f"[run] submitted: {job_id}")
    typer.echo(f"[run] done: {job_id}")
    typer.echo(f"[run] final → {out_path}")


@app.command("lint-recipe")
def run_lint_recipe(
    file: str = typer.Argument(..., help="Recipe file (.yml/.yaml/.json) to lint"),
):
    """Lint a recipe file for validity and best practices."""
    import json

    import yaml

    if not os.path.exists(file):
        typer.echo(f"Recipe not found: {file}")
        raise typer.Exit(1)

    # Load recipe file
    with open(file, "r", encoding="utf-8") as f:
        data = (
            yaml.safe_load(f) or {}
            if file.endswith((".yml", ".yaml"))
            else json.load(f)
        )

    # Basic validation
    warnings = []

    # Check for required fields
    if (
        "subject" not in data
        or not data["subject"]
        or len(str(data["subject"]).strip()) < 3
    ):
        warnings.append(
            "Missing or very short subject (should be at least 3 characters)"
        )

    # Check for system_text presence
    if "system_text" not in data or not data.get("system_text", "").strip():
        warnings.append("No system_text provided (recommended for custom behavior)")

    # Check for output path
    io_section = data.get("io", {})
    out_path = io_section.get("outPath") or io_section.get("out")
    if not out_path:
        warnings.append(
            "No output path specified (will default to books/{subject}.final.md)"
        )

    # Check for common issues
    if "styles" in data and not isinstance(data["styles"], list):
        warnings.append("styles should be a list of style names")

    if "max_chunks" in data:
        try:
            max_chunks = int(data["max_chunks"])
            if max_chunks <= 0 or max_chunks > 50:
                warnings.append(
                    "max_chunks should be between 1 and 50 for reasonable runs"
                )
        except (ValueError, TypeError):
            warnings.append("max_chunks should be a valid integer")

    # Report results
    if warnings:
        typer.echo(f"Recipe {file} has issues:")
        for i, warning in enumerate(warnings, 1):
            typer.echo(f"  {i}. {warning}")
        raise typer.Exit(1)
    else:
        typer.echo(f"✓ Recipe {file} looks good!")


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

    # Get session state for reading overlay setting
    session_state = SessionState.load_from_file(".xsarena/session_state.json")
    comp = compose_prompt(
        subject=plan_subject,
        base="zero2hero",
        overlays=overlays,
        extra_notes=extra_note,
        min_chars=L["min"],
        passes=L["passes"],
        max_chunks=total_chunks,
        apply_reading_overlay=getattr(session_state, "reading_overlay_on", False),
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
            with contextlib.suppress(Exception):
                system_text += "\n\n" + ep.read_text(encoding="utf-8", errors="ignore")

    # Output path
    if not out_path:
        out_path = f"./books/finals/{_slugify(plan_subject)}.final.md"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # Optional wait for capture
    if wait:
        typer.echo(
            "\nOpen https://lmarena.ai and add '#bridge=5102' (or your port) to the URL."
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

    warnings.warn("Using new JobsV3 system", DeprecationWarning, stacklevel=2)

    # Run the job using the orchestrator
    job_id = asyncio.run(orchestrator.run_spec(run_spec, backend_type="bridge"))

    typer.echo(f"[run] submitted: {job_id}")
    typer.echo(f"[run] done → {out_path}")


def _slugify(s: str) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "book"


@app.command("replay")
def run_replay(
    ctx: typer.Context,
    manifest_path: str = typer.Argument(..., help="Path to run manifest JSON file"),
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
):
    """Replay a job from a run manifest, warning if directive digests drift."""
    import json
    from pathlib import Path

    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        typer.echo(f"Error: Manifest file not found: {manifest_path}")
        raise typer.Exit(1)

    # Load the manifest
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    except Exception as e:
        typer.echo(f"Error loading manifest: {e}")
        raise typer.Exit(1)

    # Extract data from manifest
    final_system_text = manifest_data.get("final_system_text", "")
    resolved_run_spec_data = manifest_data.get("resolved_run_spec", {})
    directive_digests = manifest_data.get("directive_digests", {})
    config_snapshot = manifest_data.get("config_snapshot", {})

    # Create RunSpecV2 from manifest data
    from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset

    run_spec = RunSpecV2(
        subject=resolved_run_spec_data.get("subject", "replay"),
        length=LengthPreset(resolved_run_spec_data.get("length", "long")),
        span=SpanPreset(resolved_run_spec_data.get("span", "book")),
        overlays=resolved_run_spec_data.get("overlays", []),
        extra_note=resolved_run_spec_data.get("extra_note", ""),
        extra_files=resolved_run_spec_data.get("extra_files", []),
        out_path=resolved_run_spec_data.get("out_path", ""),
        profile=resolved_run_spec_data.get("profile", ""),
        generate_plan=resolved_run_spec_data.get("generate_plan", False),
        window_size=resolved_run_spec_data.get("window_size"),
        bridge_session_id=resolved_run_spec_data.get("bridge_session_id"),
        bridge_message_id=resolved_run_spec_data.get("bridge_message_id"),
    )

    # Check for directive digest drift
    import hashlib
    from pathlib import Path as P

    def calculate_current_digests(overlays, extra_files):
        """Calculate current directive digests to compare with manifest."""
        current_digests = {}

        # Calculate digests for overlays
        for overlay in overlays:
            overlay_paths = [
                P(f"directives/style/{overlay}.md"),
                P(f"directives/overlays/{overlay}.md"),
                P(f"directives/{overlay}.md"),
            ]

            for overlay_path in overlay_paths:
                if overlay_path.exists():
                    try:
                        content = overlay_path.read_text(encoding="utf-8")
                        digest = hashlib.sha256(content.encode()).hexdigest()
                        current_digests[f"overlay:{overlay}"] = digest
                        break
                    except Exception:
                        continue

        # Calculate digests for extra files
        for extra_file in extra_files:
            extra_path = P(extra_file)
            if extra_path.exists():
                try:
                    content = extra_path.read_text(encoding="utf-8")
                    digest = hashlib.sha256(content.encode()).hexdigest()
                    current_digests[f"extra:{extra_file}"] = digest
                except Exception:
                    continue

        # Calculate digest for base directive
        base_path = P("directives/base/zero2hero.md")
        if base_path.exists():
            try:
                content = base_path.read_text(encoding="utf-8")
                digest = hashlib.sha256(content.encode()).hexdigest()
                current_digests["base:zero2hero"] = digest
            except Exception:
                pass

        return current_digests

    current_digests = calculate_current_digests(run_spec.overlays, run_spec.extra_files)

    # Compare digests and warn about drift
    drift_detected = False
    for key, stored_digest in directive_digests.items():
        current_digest = current_digests.get(key)
        if current_digest and current_digest != stored_digest:
            typer.echo(f"⚠️  Directive digest drift detected: {key}")
            typer.echo(f"   Stored: {stored_digest[:12]}...")
            typer.echo(f"   Current: {current_digest[:12]}...")
            drift_detected = True

    if drift_detected:
        typer.echo(
            "⚠️  Warning: Directive digests have changed since manifest creation!"
        )
        typer.echo("   This may affect reproducibility. Continue anyway?")
        if not typer.confirm("Continue?", default=True):
            raise typer.Exit(1)

    # Use the new orchestrator system
    from ..core.v2_orchestrator.orchestrator import Orchestrator

    orchestrator = Orchestrator()

    # Submit job using the orchestrator with the original system text from manifest
    job_id = asyncio.run(orchestrator.run_spec(run_spec, backend_type="bridge"))

    typer.echo(f"[run] submitted: {job_id}")

    if follow:
        # Follow the job to completion
        from ..core.jobs.model import JobManager

        job_runner = JobManager()
        asyncio.run(job_runner.wait_for_job_completion(job_id))
        typer.echo(
            f"[run] done → {run_spec.out_path or f'./books/{run_spec.subject.replace(' ', '_')}.final.md'}"
        )
    else:
        typer.echo(
            f"[run] done → {run_spec.out_path or f'./books/{run_spec.subject.replace(' ', '_')}.final.md'}"
        )


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
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
):
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
            "\nOpen https://lmarena.ai and add '#bridge=5102'. Click Retry, then press ENTER."
        )
        try:
            input()
        except KeyboardInterrupt:
            raise typer.Exit(1)

    # Use the orchestrator to continue from file
    job_id = asyncio.run(
        orchestrator.run_continue(run_spec, str(p), until_end=until_end)
    )

    typer.echo(f"[run] submitted: {job_id}")

    if follow:
        # Follow the job to completion
        from ..core.jobs.model import JobManager

        job_runner = JobManager()
        asyncio.run(job_runner.wait_for_job_completion(job_id))
        typer.echo(f"[run/continue] done → {p}")
    else:
        typer.echo(f"[run/continue] done → {p}")


@app.command("template")
def run_template(
    ctx: typer.Context,
    template_name: str = typer.Argument(
        ..., help="Name of a directive template (e.g., kasravi_strip)."
    ),
    subject: str = typer.Argument(..., help="Subject or input text for the template."),
    out: Optional[str] = typer.Option(
        None, "--out", "-o", help="Write output to file."
    ),
):
    """Run a structured directive from the library (optionally JSON-validated if a schema exists)."""
    cli: CLIContext = ctx.obj

    found = find_directive(template_name)
    if not found:
        typer.echo(f"Error: directive '{template_name}' not found.", err=True)
        raise typer.Exit(1)
    prompt_path, schema_path = found
    system_prompt = prompt_path.read_text(encoding="utf-8")

    user_prompt = subject
    if "{SUBJECT}" in system_prompt or "{SOURCE_TEXT}" in system_prompt:
        system_prompt = system_prompt.replace("{SUBJECT}", subject).replace(
            "{SOURCE_TEXT}", subject
        )
        user_prompt = "Process the request as defined in the system prompt."

    result = asyncio.run(
        cli.engine.send_and_collect(user_prompt, system_prompt=system_prompt)
    )

    # Optional schema validation (if installed and a schema exists)
    if schema_path:
        try:
            try:
                import jsonschema  # optional dependency
            except Exception:
                jsonschema = None
            if jsonschema is not None:
                m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", result, re.DOTALL)
                json_text = m.group(1) if m else result
                output_json = json.loads(json_text)
                schema_json = json.loads(schema_path.read_text(encoding="utf-8"))
                jsonschema.validate(instance=output_json, schema=schema_json)
                typer.echo("✅ JSON output is valid against schema.")
            else:
                typer.echo("(jsonschema not installed; skipping validation)")
        except Exception as e:
            typer.echo(f"❌ JSON validation failed: {e}", err=True)

    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(result, encoding="utf-8")
        typer.echo(f"→ {out}")
    else:
        typer.echo(result)
