# src/xsarena/cli/cmds_playground.py
from __future__ import annotations
from pathlib import Path
import typer
from pydantic import BaseModel

app = typer.Typer(help="A playground for testing prompts.")

class PlaygroundSpec(BaseModel):
    prompt_file: Path
    subject: str

@app.command("run")
def run_playground(prompt_file: Path = typer.Argument(..., exists=True), subject: str = typer.Argument(...)):
    """Run a prompt against a subject in the playground."""
    spec = PlaygroundSpec(prompt_file=prompt_file, subject=subject)
    typer.echo("Running playground (placeholder)...")
    typer.echo(f"Prompt File: {spec.prompt_file.name}")
    typer.echo(f"Subject: {spec.subject}")