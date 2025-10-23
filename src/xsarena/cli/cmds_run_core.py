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


from ..core.specs import DEFAULT_PROFILES
from ..core.v2_orchestrator.orchestrator import Orchestrator
from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset
from .context import CLIContext


def run_book(
    ctx: typer.Context,
    subject: str,
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
) -> str:
    """
    Generate a book with specified subject.
    """
    cli_ctx: CLIContext = ctx.obj
    orch = Orchestrator()

    # Load profiles
    profiles = {**DEFAULT_PROFILES, **load_profiles()}

    # Get profile configuration
    profile_config = profiles.get(profile or "zero2hero", {})
    overlays = profile_config.get("overlays", [])

    # Convert extra_file paths to strings
    extra_files = [str(ef) for ef in extra_file if ef.exists()]

    # Normalize legacy enum values to lower case for compatibility
    normalized_length = length.lower() if isinstance(length, str) else length
    normalized_span = span.lower() if isinstance(span, str) else span

    # Build the run spec
    run_spec = RunSpecV2(
        subject=subject,
        length=LengthPreset(normalized_length),
        span=SpanPreset(normalized_span),
        overlays=overlays,
        extra_files=extra_files,
        out_path=out,
        generate_plan=bool(plan),
        profile=profile,
        backend=cli_ctx.state.backend,
        model=cli_ctx.state.model,
    )

    if follow:
        job_id = asyncio.run(
            orch.run_spec(run_spec, backend_type=cli_ctx.state.backend)
        )
        typer.echo(f"Job submitted: {job_id}")
        typer.echo("Following job to completion...")
    else:
        job_id = asyncio.run(
            orch.run_spec(run_spec, backend_type=cli_ctx.state.backend)
        )
        typer.echo(f"Job submitted: {job_id}")
        typer.echo(f"Run 'xsarena ops jobs follow {job_id}' to monitor progress")


def run_write(
    ctx: typer.Context,
    subject: str,
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
) -> str:
    """
    Write content with specified subject (alias for run_book).
    """
    run_book(ctx, subject, profile, length, span, extra_file, out, wait, plan, follow)
