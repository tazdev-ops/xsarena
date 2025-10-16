import pathlib

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
            if file.endswith((".yml", ".yaml")):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
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
        cli: CLIContext = typer.get_current_context().obj
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
        # Run the job using JobRunner
        task = data.get("task", "book.zero2hero")
        io = data.get("io", {})
        out_path = io.get("outPath") or io.get("out")
        cont = data.get("continuation", {})
        max_chunks = int(data.get("max_chunks", 8))

        playbook = {
            "name": f"CLI recipe: {subject}",
            "subject": subject,
            "task": task,
            "system_text": system_text,
            "hammer": True,
            "outline_first": True,
            "failover": {
                "watchdog_secs": 90,
                "max_retries": 3,
                "fallback_backend": "openrouter",
            },
        }

        params = {
            "max_chunks": max_chunks,
            "continuation": {
                "mode": cont.get("mode", "anchor"),
                "minChars": int(cont.get("minChars", 3000)),
                "pushPasses": int(cont.get("pushPasses", 1)),
                "repeatWarn": bool(cont.get("repeatWarn", True)),
            },
            "io": {"outPath": out_path} if out_path else {},
        }

        runner = JobRunner({})
        job_id = runner.submit(playbook, params)
        typer.echo(f"[jobs] submitted: {job_id}")
        runner.run_job(job_id)
        typer.echo(f"[jobs] done: {job_id}")
