"""Book mode CLI commands for XSArena."""

import asyncio
from typing import Optional

import typer

from ..modes.book import BookMode
from .context import CLIContext

app = typer.Typer()


@app.command("zero2hero")
def book_zero2hero(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic for the zero-to-hero book"),
    outline: Optional[str] = typer.Option(None, help="Existing outline to follow"),
):
    """Create a comprehensive book from zero to hero level."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.zero2hero(topic, outline))
    print(result)


@app.command("reference")
def book_reference(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic for the reference book"),
):
    """Create a reference-style book with detailed information."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.reference(topic))
    print(result)


@app.command("pop")
def book_pop(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic for the popular science book"),
):
    """Create a popular science/book style content."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.pop(topic))
    print(result)


@app.command("nobs")
def book_nobs(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic for the no-bullshit manual"),
):
    """Create a no-bullshit manual about the topic."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.nobs(topic))
    print(result)


@app.command("outline")
def book_outline(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic for the book outline"),
):
    """Generate a detailed outline for a book."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.generate_outline(topic))
    print(result)


@app.command("polish")
def book_polish(
    ctx: typer.Context, text: str = typer.Argument(..., help="Text to polish")
):
    """Polish text by tightening prose and removing repetition."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.polish_text(text))
    print(result)


@app.command("shrink")
def book_shrink(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to shrink to 70% length"),
):
    """Shrink text to 70% of original length while preserving facts."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.shrink_text(text))
    print(result)


@app.command("critique")
def book_critique(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to critique for repetition and flow"),
):
    """Critique text for repetition, flow issues, and clarity."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.critique_text(text))
    print(result)


@app.command("diagram")
def book_diagram(
    ctx: typer.Context,
    description: str = typer.Argument(
        ..., help="Description of the diagram to generate"
    ),
):
    """Generate a Mermaid diagram description."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.generate_diagram(description))
    print(result)



