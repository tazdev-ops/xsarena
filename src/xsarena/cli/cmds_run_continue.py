from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

import typer

try:
    from ..core.profiles import load_profiles
except ImportError:
    # Fallback if profiles module doesn't exist
    def load_profiles():
        return {}


from ..core.prompt import compose_prompt
from ..core.specs import DEFAULT_PROFILES
from ..core.v2_orchestrator.orchestrator import Orchestrator
from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset
from .context import CLIContext

# Local fallbacks
LENGTH_PRESETS = {
    "standard": {"min": 4200, "passes": 1},
    "long": {"min": 5800, "passes": 3},
    "very-long": {"min": 6200, "passes": 4},
    "max": {"min": 6800, "passes": 5},
}

SPAN_PRESETS = {"medium": 12, "long": 24, "book": 40}


def slugify(s, default="book"):
    """Convert string to a URL-friendly slug."""
    import re

    # Replace non-alphanumeric characters with underscores
    slug = re.sub(r"[^a-zA-Z0-9]", "_", s)
    # Strip leading/trailing underscores
    slug = slug.strip("_")
    # Return default if empty after processing
    return slug if slug else default


def run_continue(
    file_path: Path,
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Use a specific profile"
    ),
    length: str = typer.Option(
        "standard", "--length", help="Length preset: standard|long|very-long|max"
    ),
    span: str = typer.Option("medium", "--span", help="Span preset: medium|long|book"),
    extra_file: List[Path] = typer.Option(
        [], "--extra-file", help="Append file(s) to system prompt"
    ),
    out: Optional[str] = typer.Option(None, "--out", "-o", help="Output path"),
    wait: bool = typer.Option(
        False, "--wait", help="Wait for browser capture before starting"
    ),
    plan: bool = typer.Option(False, "--plan", help="Generate an outline first"),
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
    until_end: bool = typer.Option(
        False, "--until-end", help="Continue until end of file"
    ),
    ctx: typer.Context = typer.Context,
) -> str:
    """
    Continue writing from an existing file.
    """
    cli_ctx: CLIContext = ctx.obj
    orch = Orchestrator()

    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(1)

    # Load the file content to get the subject
    content = file_path.read_text(encoding="utf-8")
    # Extract subject from filename or use a default
    subject = file_path.stem.replace("_", " ").title()

    # Load profiles
    profiles = {**DEFAULT_PROFILES, **load_profiles()}

    # Get profile configuration
    profile_config = profiles.get(profile or "zero2hero", {})
    base_prompt = profile_config.get("base", "zero2hero")
    overlays = profile_config.get("overlays", [])

    # Map length preset to values
    length_config = LENGTH_PRESETS.get(length, LENGTH_PRESETS["standard"])
    min_chars = length_config["min"]
    passes = length_config["passes"]

    # Map span preset to values
    max_chunks = SPAN_PRESETS.get(span, SPAN_PRESETS["medium"])

    # Prepare system text from extra files
    system_text = ""
    for ef in extra_file:
        if ef.exists():
            system_text += (
                f"\\n\\n{ef.name.upper()}:\\n{ef.read_text(encoding='utf-8')}"
            )

    # Compose the prompt
    prompt_parts = compose_prompt(
        subject=subject,
        base=base_prompt,
        overlays=overlays,
        system_text=system_text,
        profile=profile_config,
    )

    # Build the run spec
    run_spec = RunSpecV2(
        task="continue",
        subject=subject,
        length=LengthPreset(length),
        span=SpanPreset(span),
        min_length=min_chars,
        passes=passes,
        chunks=max_chunks,
        backend=cli_ctx.cfg.backend,
        model=cli_ctx.cfg.model,
        out_path=out or str(file_path),
        system_text=prompt_parts["system"],
        user_text=prompt_parts["user"],
    )

    # Submit the continue job
    job_id = orch.submit_continue(
        run_spec,
        str(file_path),
        until_end=until_end,
        system_text=system_text,
        session_state=cli_ctx.session_state,
    )

    if follow:
        typer.echo(f"Continue job submitted: {job_id}")
        typer.echo("Following job to completion...")
        asyncio.run(orch.follow_job(job_id))
    else:
        typer.echo(f"Continue job submitted: {job_id}")
        typer.echo(f"Run 'xsarena ops jobs follow {job_id}' to monitor progress")
