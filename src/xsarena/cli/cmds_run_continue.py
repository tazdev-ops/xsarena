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
    overlays = profile_config.get("overlays", [])

    # Convert extra_file paths to strings
    extra_files = [str(ef) for ef in extra_file if ef.exists()]

    # Build the run spec
    run_spec = RunSpecV2(
        subject=subject,
        length=LengthPreset(length),
        span=SpanPreset(span),
        overlays=overlays,
        extra_files=extra_files,
        out_path=out or str(file_path),
        profile=profile,
        backend=cli_ctx.cfg.backend,
        model=cli_ctx.cfg.model,
    )

    if follow:
        job_id = asyncio.run(
            orch.run_continue(run_spec, str(file_path), until_end=until_end, priority=5)
        )
        typer.echo(f"Continue job submitted: {job_id}")
        typer.echo("Following job to completion...")
    else:
        job_id = asyncio.run(
            orch.run_continue(run_spec, str(file_path), until_end=until_end, priority=5)
        )
        typer.echo(f"Continue job submitted: {job_id}")
        typer.echo(f"Run 'xsarena ops jobs follow {job_id}' to monitor progress")
