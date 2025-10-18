#!/usr/bin/env python3
import asyncio
from pathlib import Path

import typer

from ..core.backends import create_backend
from ..core.engine import Engine
from ..core.state import SessionState
from ..utils.chapter_splitter import export_chapters
from ..utils.extractors import (
    extract_checklists_from_file,
    generate_checklist_report,
)

app = typer.Typer(help="Fun explainers, personas, and toggles")


@app.command("eli5")
def fun_eli5(topic: str):
    try:
        eng = Engine(create_backend("openrouter"), SessionState())
    except ValueError:
        typer.echo(
            "Error: OpenRouter backend requires OPENROUTER_API_KEY environment variable to be set.",
            err=True,
        )
        raise typer.Exit(1)
    sys = "Explain like I'm five (ELI5): plain, short sentences; vivid but accurate analogies; 120–180 words."
    print(asyncio.run(eng.send_and_collect(topic, system_prompt=sys)))


@app.command("story")
def fun_story(concept: str):
    try:
        eng = Engine(create_backend("openrouter"), SessionState())
    except ValueError:
        typer.echo(
            "Error: OpenRouter backend requires OPENROUTER_API_KEY environment variable to be set.",
            err=True,
        )
        raise typer.Exit(1)
    sys = "Explain the concept with a short story that aids memory. 200–300 words; accurate; one clear moral at end."
    print(asyncio.run(eng.send_and_collect(concept, system_prompt=sys)))


@app.command("persona")
def fun_persona(name: str):
    """chad|prof|coach — set persona overlay (session, not global)"""
    overlays = {
        "chad": "Persona: Chad — decisive, evidence-first, no fluff; end with Bottom line.",
        "prof": "Persona: Professor — structured, cites sources sparingly, neutral tone.",
        "coach": "Persona: Coach — encouraging, actionable next steps, no fluff.",
    }
    print(overlays.get(name.lower(), "Unknown persona. Try chad|prof|coach."))


@app.command("nobs")
def fun_nobs(flag: str):
    """on|off — alias to no‑BS"""
    if flag.lower() not in ("on", "off"):
        print("Use: xsarena fun nobs on|off")
        return
    print(f"(alias) Run: /style.nobs {flag.lower()}")


@app.command("export-chapters")
def export_chapters_cmd(
    book: str = typer.Argument(..., help="Path to the book file to split"),
    output_dir: str = typer.Option(
        "./books/chapters", "--out", help="Output directory for chapters"
    ),
):
    """Export a book into chapters with navigation links."""

    book_path = Path(book)
    if not book_path.exists():
        typer.echo(f"Error: Book file not found at '{book}'")
        raise typer.Exit(1)

    try:
        chapters = export_chapters(str(book_path), output_dir)
        typer.echo(f"Successfully exported {len(chapters)} chapters to {output_dir}/")
        typer.echo(f"Table of contents created at {output_dir}/toc.md")
    except Exception as e:
        typer.echo(f"Error exporting chapters: {e}", err=True)
        raise typer.Exit(1)


@app.command("extract-checklists")
def extract_checklists_cmd(
    book: str = typer.Option(
        ..., "--book", help="Path to the book file to extract checklists from"
    ),
    output: str = typer.Option(
        "./books/checklists", "--out", help="Output directory for checklists"
    ),
):
    """Extract checklist items from a book, grouped by sections."""
    book_path = Path(book)
    if not book_path.exists():
        typer.echo(f"Error: Book file not found at '{book}'")
        raise typer.Exit(1)

    # Create output directory
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract checklist items
    typer.echo("Extracting checklist items...")
    items = extract_checklists_from_file(str(book_path))

    # Generate report
    report = generate_checklist_report(items, str(book_path))

    # Create output filename based on input book name
    book_name = book_path.stem
    output_file = output_dir / f"{book_name}_checklist.md"

    # Save report
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(output_file).write_text(report, encoding="utf-8")

    typer.echo("Checklist extraction complete!")
    typer.echo(f"Found {len(items)} checklist items")
    typer.echo(f"Checklist saved to: {output_file}")
