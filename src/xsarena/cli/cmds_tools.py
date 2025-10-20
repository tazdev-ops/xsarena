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
    result = asyncio.run(eng.send_and_collect(topic, system_prompt=sys))
    typer.echo(result)


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
    result = asyncio.run(eng.send_and_collect(concept, system_prompt=sys))
    typer.echo(result)


@app.command("persona")
def fun_persona(name: str):
    """chad|prof|coach — set persona overlay (session, not global)"""
    overlays = {
        "chad": "Persona: Chad — decisive, evidence-first, no fluff; end with Bottom line.",
        "prof": "Persona: Professor — structured, cites sources sparingly, neutral tone.",
        "coach": "Persona: Coach — encouraging, actionable next steps, no fluff.",
    }
    typer.echo(overlays.get(name.lower(), "Unknown persona. Try chad|prof|coach."))


@app.command("nobs")
def fun_nobs(flag: str):
    """on|off — alias to no‑BS"""
    if flag.lower() not in ("on", "off"):
        typer.echo("Use: xsarena tools nobs on|off")
        return
    typer.echo(f"(alias) Run: /style.nobs {flag.lower()}")


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


@app.command("tldr")
def fun_tldr(
    file: str = typer.Argument(..., help="Path to the file to summarize"),
    bullets: int = typer.Option(
        7, "--bullets", "-b", help="Number of bullet points for summary"
    ),
    output_file: str = typer.Option(None, "--out", help="Output file for the summary"),
):
    """Create a tight summary with callouts from a text file."""
    import asyncio
    from pathlib import Path

    file_path = Path(file)
    if not file_path.exists():
        typer.echo(f"Error: File '{file}' not found.")
        raise typer.Exit(1)

    content = file_path.read_text(encoding="utf-8")

    # Create a system prompt for TL;DR generation
    system_prompt = (
        f"You create tight, actionable summaries with key callouts. "
        f"Extract the most important points in {bullets} bullet points maximum. "
        f"Include: 'So what?' (key insight), 'Action items' (2-3 concrete steps), "
        f"and 'Glossary' (3 key terms with definitions). "
        f"Keep it concise and preserve the core meaning."
    )

    prompt = f"Please create a TL;DR summary of the following content:\n\n{content}"

    # Use the engine to generate the summary
    try:
        from ..core.backends import create_backend
        from ..core.state import SessionState

        eng = Engine(create_backend("openrouter"), SessionState())
        result = asyncio.run(eng.send_and_collect(prompt, system_prompt=system_prompt))

        if output_file:
            output_path = Path(output_file)
            output_path.write_text(result, encoding="utf-8")
            typer.echo(f"TL;DR summary saved to {output_file}")
        else:
            typer.echo(result)
    except Exception as e:
        typer.echo(f"Error generating TL;DR: {e}", err=True)
        raise typer.Exit(1)
