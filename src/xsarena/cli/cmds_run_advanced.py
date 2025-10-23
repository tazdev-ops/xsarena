from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
import yaml
from pydantic import BaseModel, ConfigDict, Field

try:
    from ..core.profiles import load_profiles
except ImportError:
    # Fallback if profiles module doesn't exist
    def load_profiles():
        return {}


from ..core.specs import DEFAULT_PROFILES
from ..core.v2_orchestrator.orchestrator import Orchestrator
from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset
from ..utils.directives import find_directive
from .context import CLIContext


class RecipeV2(BaseModel):
    """Version 2 recipe specification with typed fields and validation."""

    subject: str = Field(..., description="The subject to generate content about")
    length: str = Field("standard", description="Length preset for the run")
    span: str = Field("medium", description="Span preset for the run")
    overlays: List[str] = Field(
        default_factory=list, description="Overlay specifications"
    )
    extra_files: List[str] = Field(
        default_factory=list, description="Additional files to include"
    )
    out_path: Optional[str] = Field(None, description="Output path for the result")
    generate_plan: bool = Field(False, description="Generate an outline first")

    model_config = ConfigDict(extra="forbid")  # Forbid extra fields to catch typos


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


def run_from_recipe(
    ctx: typer.Context,
    recipe_path: Path,
    out: Optional[str] = typer.Option(None, "--out", "-o", help="Output path"),
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
) -> str:
    """
    Run a job from a recipe file.
    """
    cli_ctx: CLIContext = ctx.obj
    orch = Orchestrator()

    if not recipe_path.exists():
        typer.echo(f"Error: Recipe file not found: {recipe_path}", err=True)
        raise typer.Exit(1)

    # Load recipe
    recipe_content = recipe_path.read_text(encoding="utf-8")
    recipe_data = yaml.safe_load(recipe_content)

    # Validate recipe using RecipeV2 model
    try:
        recipe = RecipeV2.model_validate(recipe_data)
    except Exception as e:
        typer.echo(f"Error: Invalid recipe format: {e}", err=True)
        raise typer.Exit(1)

    # Build the run spec with validated fields
    run_spec = RunSpecV2(
        subject=recipe.subject,
        length=(
            LengthPreset(recipe.length)
            if recipe.length in ["standard", "long", "very-long", "max"]
            else LengthPreset.STANDARD
        ),
        span=(
            SpanPreset(recipe.span)
            if recipe.span in ["medium", "long", "book"]
            else SpanPreset.MEDIUM
        ),
        overlays=recipe.overlays,
        extra_files=recipe.extra_files,
        out_path=recipe.out_path or out,
        generate_plan=recipe.generate_plan,
        backend=cli_ctx.state.backend,
        model=cli_ctx.state.model,
    )

    if follow:
        job_id = asyncio.run(
            orch.run_spec(run_spec, backend_type=cli_ctx.state.backend)
        )
        typer.echo(f"Recipe job submitted: {job_id}")
        typer.echo("Following job to completion...")
    else:
        job_id = asyncio.run(
            orch.run_spec(run_spec, backend_type=cli_ctx.state.backend)
        )
        typer.echo(f"Recipe job submitted: {job_id}")
        typer.echo(f"Run 'xsarena ops jobs follow {job_id}' to monitor progress")


def run_lint_recipe(
    ctx: typer.Context,
    recipe_path: Path,
) -> None:
    """
    Lint a recipe file for syntax errors.
    """
    if not recipe_path.exists():
        typer.echo(f"Error: Recipe file not found: {recipe_path}", err=True)
        raise typer.Exit(1)

    try:
        recipe_content = recipe_path.read_text(encoding="utf-8")
        recipe = yaml.safe_load(recipe_content)
        typer.echo(f"✓ Recipe {recipe_path} is valid YAML")

        # Basic validation
        required_fields = ["subject"]
        missing_fields = [field for field in required_fields if field not in recipe]
        if missing_fields:
            typer.echo(f"⚠️  Missing required fields: {', '.join(missing_fields)}")
        else:
            typer.echo("✓ Recipe has all required fields")

    except yaml.YAMLError as e:
        typer.echo(f"❌ YAML syntax error in {recipe_path}: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error validating recipe: {e}", err=True)
        raise typer.Exit(1)


def run_from_plan(
    ctx: typer.Context,
    seeds: List[str] = typer.Argument(..., help="Rough seeds to generate plan from"),
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
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
) -> str:
    """
    Plan from rough seeds and run a book.
    """
    cli_ctx: CLIContext = ctx.obj
    orch = Orchestrator()

    # Combine seeds into a subject
    subject = f"Plan from seeds: {' '.join(seeds)}"

    # Load profiles
    profiles = {**DEFAULT_PROFILES, **load_profiles()}

    # Get profile configuration
    profile_config = profiles.get(profile or "zero2hero", {})
    overlays = profile_config.get("overlays", [])

    # Build the run spec with generate_plan=True
    run_spec = RunSpecV2(
        subject=subject,
        length=LengthPreset(length),
        span=SpanPreset(span),
        overlays=overlays,
        extra_files=[str(ef) for ef in extra_file if ef.exists()],
        out_path=out,
        generate_plan=True,
        backend=cli_ctx.state.backend,
        model=cli_ctx.state.model,
    )

    # Submit the job
    job_id = asyncio.run(orch.run_spec(run_spec, backend_type=cli_ctx.state.backend))

    if follow:
        typer.echo(f"Plan job submitted: {job_id}")
        typer.echo("Following job to completion...")
    else:
        typer.echo(f"Plan job submitted: {job_id}")
        typer.echo(f"Run 'xsarena ops jobs follow {job_id}' to monitor progress")


def run_replay(
    ctx: typer.Context,
    manifest_path: Path,
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
) -> str:
    """
    Replay a job from a run manifest.
    """
    typer.echo(
        "Not implemented for v0.3 manifests yet. Use: xsarena ops jobs clone and rerun."
    )
    raise typer.Exit(2)


def run_template(
    ctx: typer.Context,
    template_name: str,
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
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
) -> str:
    """
    Run a structured directive from the template library.
    """
    cli_ctx: CLIContext = ctx.obj
    orch = Orchestrator()

    # Find the template directive
    tmpl = find_directive(f"templates/{template_name}")
    if not tmpl:
        typer.echo(f"Error: Template '{template_name}' not found", err=True)
        raise typer.Exit(1)

    # Unpack the template
    prompt_path, _ = tmpl

    # Load profiles
    profiles = {**DEFAULT_PROFILES, **load_profiles()}

    # Get profile configuration
    profile_config = profiles.get(profile or "zero2hero", {})
    overlays = profile_config.get("overlays", [])

    # Build the run spec
    run_spec = RunSpecV2(
        subject=f"{template_name}: {subject}",
        length=LengthPreset(length),
        span=SpanPreset(span),
        overlays=overlays,
        extra_files=[str(prompt_path)] + [str(ef) for ef in extra_file if ef.exists()],
        out_path=out,
        backend=cli_ctx.state.backend,
        model=cli_ctx.state.model,
    )

    # Submit the job
    job_id = asyncio.run(orch.run_spec(run_spec, backend_type=cli_ctx.state.backend))

    if follow:
        typer.echo(f"Template job submitted: {job_id}")
        typer.echo("Following job to completion...")
    else:
        typer.echo(f"Template job submitted: {job_id}")
        typer.echo(f"Run 'xsarena ops jobs follow {job_id}' to monitor progress")
