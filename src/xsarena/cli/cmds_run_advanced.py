from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
import yaml

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
from ..utils.directives import find_directive
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


def run_from_recipe(
    recipe_path: Path,
    out: Optional[str] = typer.Option(None, "--out", "-o", help="Output path"),
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
    ctx: typer.Context = typer.Context,
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
    recipe = yaml.safe_load(recipe_content)

    # Extract supported parameters from recipe
    subject = recipe.get("subject", "Recipe Output")
    length = recipe.get("length", "standard")
    span = recipe.get("span", "medium")
    overlays = recipe.get("overlays", [])
    extra_files = recipe.get("extra_files", [])
    generate_plan = recipe.get("generate_plan", False)

    # Build the run spec with only supported fields
    run_spec = RunSpecV2(
        subject=subject,
        length=LengthPreset(length)
        if length in ["standard", "long", "very-long", "max"]
        else LengthPreset.STANDARD,
        span=SpanPreset(span)
        if span in ["medium", "long", "book"]
        else SpanPreset.MEDIUM,
        overlays=overlays,
        extra_files=extra_files,
        out_path=recipe.get("out_path", out),
        generate_plan=generate_plan,
        backend=cli_ctx.cfg.backend,
        model=cli_ctx.cfg.model,
    )

    if follow:
        job_id = asyncio.run(orch.run_spec(run_spec, backend_type=cli_ctx.cfg.backend))
        typer.echo(f"Recipe job submitted: {job_id}")
        typer.echo("Following job to completion...")
    else:
        job_id = asyncio.run(orch.run_spec(run_spec, backend_type=cli_ctx.cfg.backend))
        typer.echo(f"Recipe job submitted: {job_id}")
        typer.echo(f"Run 'xsarena ops jobs follow {job_id}' to monitor progress")


def run_lint_recipe(
    recipe_path: Path,
    ctx: typer.Context = typer.Context,
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
    ctx: typer.Context = typer.Context,
) -> str:
    """
    Plan from rough seeds and run a book.
    """
    cli_ctx: CLIContext = ctx.obj
    orch = Orchestrator()

    # Combine seeds into a plan prompt
    seeds_text = "\\n".join(seeds)
    subject = f"Plan from seeds: {' '.join(seeds[:3])}"  # Use first 3 seeds as subject

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

    # Compose the prompt for planning
    prompt_parts = compose_prompt(
        subject=subject,
        base="plan_from_seeds",
        overlays=overlays,
        system_text=system_text,
        profile=profile_config,
    )

    # Build the run spec
    run_spec = RunSpecV2(
        task="plan",
        subject=subject,
        length=LengthPreset(length),
        span=SpanPreset(span),
        min_length=min_chars,
        passes=passes,
        chunks=max_chunks,
        backend=cli_ctx.cfg.backend,
        model=cli_ctx.cfg.model,
        out_path=out,
        system_text=prompt_parts["system"],
        user_text=f"{prompt_parts['user']}\\n\\nSEEDS:\\n{seeds_text}",
    )

    # Submit the job
    job_id = orch.submit(
        run_spec, system_text=system_text, session_state=cli_ctx.session_state
    )

    if follow:
        typer.echo(f"Plan job submitted: {job_id}")
        typer.echo("Following job to completion...")
        asyncio.run(orch.follow_job(job_id))
    else:
        typer.echo(f"Plan job submitted: {job_id}")
        typer.echo(f"Run 'xsarena ops jobs follow {job_id}' to monitor progress")


def run_replay(
    manifest_path: Path,
    follow: bool = typer.Option(
        False, "--follow", help="Submit job and follow to completion"
    ),
    ctx: typer.Context = typer.Context,
) -> str:
    """
    Replay a job from a run manifest.
    """
    typer.echo(
        "Not implemented for v0.3 manifests yet. Use: xsarena ops jobs clone and rerun."
    )
    raise typer.Exit(2)


def run_template(
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
    ctx: typer.Context = typer.Context,
) -> str:
    """
    Run a structured directive from the template library.
    """
    cli_ctx: CLIContext = ctx.obj
    orch = Orchestrator()

    # Find the template directive
    template_path = find_directive(f"templates/{template_name}")
    if not template_path or not template_path.exists():
        typer.echo(f"Error: Template '{template_name}' not found", err=True)
        raise typer.Exit(1)

    # Load template content
    template_content = template_path.read_text(encoding="utf-8")

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

    # Prepare system text from extra files and template
    system_text = template_content
    for ef in extra_file:
        if ef.exists():
            system_text += (
                f"\\n\\n{ef.name.upper()}:\\n{ef.read_text(encoding='utf-8')}"
            )

    # Build the run spec
    run_spec = RunSpecV2(
        task="template",
        subject=f"{template_name}: {subject}",
        length=LengthPreset(length),
        span=SpanPreset(span),
        min_length=min_chars,
        passes=passes,
        chunks=max_chunks,
        backend=cli_ctx.cfg.backend,
        model=cli_ctx.cfg.model,
        out_path=out,
        system_text=system_text,
        user_text=subject,
    )

    # Submit the job
    job_id = orch.submit(
        run_spec, system_text=system_text, session_state=cli_ctx.session_state
    )

    if follow:
        typer.echo(f"Template job submitted: {job_id}")
        typer.echo("Following job to completion...")
        asyncio.run(orch.follow_job(job_id))
    else:
        typer.echo(f"Template job submitted: {job_id}")
        typer.echo(f"Run 'xsarena ops jobs follow {job_id}' to monitor progress")
