"""Pipeline CLI commands for XSArena."""

import json
import os

import typer

from ..core.pipeline import run_pipeline

app = typer.Typer()


def _load_yaml_or_json(path: str) -> dict:
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        with open(path, "r", encoding="utf-8") as f:
            import json

            return json.load(f)


@app.command("run")
def pipeline_run(
    file: str = typer.Argument(..., help="Pipeline file (.yml/.yaml/.json)"),
    apply: bool = typer.Option(
        False, "--apply", help="Execute steps (default: dry-run)"
    ),
):
    """Run a project pipeline (fix → test → format → commit)."""
    if not os.path.exists(file):
        typer.echo(f"Pipeline file not found: {file}")
        raise typer.Exit(1)
    try:
        data = _load_yaml_or_json(file)
    except Exception as e:
        typer.echo(f"Failed to load pipeline: {e}")
        raise typer.Exit(1)
    steps = data.get("steps") or []
    if not isinstance(steps, list):
        typer.echo("Invalid pipeline format: missing steps list")
        raise typer.Exit(1)
    results = run_pipeline(steps, apply=apply)
    typer.echo(json.dumps(results, indent=2))
