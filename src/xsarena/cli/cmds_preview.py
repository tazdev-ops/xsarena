import pathlib
import re

import typer

from .context import CLIContext

app = typer.Typer(help="Preview final prompt + style sample before running a recipe")


def _ppaths(subject: str):
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in subject.lower())
    base = pathlib.Path("directives/_preview")
    base.mkdir(parents=True, exist_ok=True)
    return (base / f"{slug}.prompt.md", base / f"{slug}.preview.md")


@app.command("run")
def preview_run(
    ctx: typer.Context,
    file: str = typer.Argument(...),
    edit: bool = typer.Option(True, "--edit/--no-edit"),
    autorun: bool = typer.Option(False, "--autorun/--no-autorun"),
    sample: bool = typer.Option(
        False,
        "--sample/--no-sample",
        help="Generate a real 2-4 paragraph sample using the engine",
    ),
):
    """Preview a recipe before running it."""
    import json

    import yaml

    # Load the recipe file
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = (
                yaml.safe_load(f) if file.endswith((".yml", ".yaml")) else json.load(f)
            )
    except Exception as e:
        typer.echo(f"Failed to load recipe file: {e}", err=True)
        raise typer.Exit(2)

    subject = data.get("subject") or "book"
    system_text = (data.get("system_text") or "").strip()

    if not system_text:
        typer.echo("No system_text found in recipe; cannot preview.", err=True)
        raise typer.Exit(2)

    p_prompt, p_sample = _ppaths(subject)
    p_prompt.write_text(system_text + "\n", encoding="utf-8")
    typer.echo(f"[preview] Prompt → {p_prompt}")

    if edit:
        edited = typer.edit(system_text)
        if edited:
            system_text = edited.strip()
            p_prompt.write_text(system_text + "\n", encoding="utf-8")
            typer.echo("[preview] Prompt updated.")

    # Generate a real sample if requested
    if sample:
        cli: CLIContext = ctx.obj
        import asyncio

        # Generate a sample using the current engine
        sample_prompt = "Write a 2-paragraph sample in the style implied by the system prompt. No NEXT line. No outline."
        try:
            sample_text = asyncio.run(
                cli.engine.send_and_collect(sample_prompt, system_prompt=system_text)
            )
            p_sample.write_text(sample_text + "\n", encoding="utf-8")
            typer.echo(f"[preview] Real sample generated → {p_sample}")
        except Exception as e:
            typer.echo(f"[preview] Failed to generate sample: {e}", err=True)
            # Fallback to placeholder
            sample_content = f"# Preview Sample for {subject}\n\nThis is a preview sample generated from the recipe.\n\nThe actual implementation would connect to the configured backend to generate a 2-4 paragraph style sample based on the system prompt."
            p_sample.write_text(sample_content + "\n", encoding="utf-8")
            typer.echo(f"[preview] Sample → {p_sample}")
    else:
        # For now, we'll just create a simple preview sample without calling the backend
        # In a real implementation, you would call the backend to generate the sample
        sample_content = f"# Preview Sample for {subject}\n\nThis is a preview sample generated from the recipe.\n\nThe actual implementation would connect to the configured backend to generate a 2-4 paragraph style sample based on the system prompt."
        p_sample.write_text(sample_content + "\n", encoding="utf-8")
        typer.echo(f"[preview] Sample → {p_sample}")

    if autorun:
        # Use the new orchestrator system
        import asyncio

        from ..core.v2_orchestrator.orchestrator import Orchestrator
        from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset

        # Compute a sane slug for the subject
        slug = re.sub(r"[^\w\s-]", "", subject.lower()).strip()
        slug = re.sub(r"[-\s]+", "_", slug)
        if not slug:
            slug = "book"

        default_out = f"./books/{slug}.final.md"
        run_spec = RunSpecV2(
            subject=subject,
            length=LengthPreset.LONG,
            span=SpanPreset.BOOK,
            overlays=["narrative", "no_bs"],
            extra_note="",
            extra_files=[],
            out_path=default_out,
            profile="",
        )

        orchestrator = Orchestrator()
        job_id = asyncio.run(orchestrator.run_spec(run_spec, backend_type="bridge"))

        # Use a single variable for echoes to avoid nested f-strings/quoting issues
        echo_message = (
            f"[run] submitted: {job_id}\n"
            f"[run] done: {job_id}\n"
            f"[run] final → {default_out}"
        )
        typer.echo(echo_message)
