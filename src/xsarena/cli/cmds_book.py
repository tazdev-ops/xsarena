"""Book mode CLI commands for XSArena."""

import asyncio
from typing import Optional

import typer

from .context import CLIContext
from ..modes.book import BookMode

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
    topic: str = typer.Argument(..., help="Topic for the reference book")
):
    """Create a reference-style book with detailed information."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.reference(topic))
    print(result)


@app.command("pop")
def book_pop(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic for the popular science book")
):
    """Create a popular science/book style content."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.pop(topic))
    print(result)


@app.command("nobs")
def book_nobs(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic for the no-bullshit manual")
):
    """Create a no-bullshit manual about the topic."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.nobs(topic))
    print(result)


@app.command("outline")
def book_outline(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic for the book outline")
):
    """Generate a detailed outline for a book."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.generate_outline(topic))
    print(result)


@app.command("polish")
def book_polish(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to polish")
):
    """Polish text by tightening prose and removing repetition."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.polish_text(text))
    print(result)


@app.command("shrink")
def book_shrink(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to shrink to 70% length")
):
    """Shrink text to 70% of original length while preserving facts."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.shrink_text(text))
    print(result)


@app.command("critique")
def book_critique(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to critique for repetition and flow")
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
    )
):
    """Generate a Mermaid diagram description."""
    cli: CLIContext = ctx.obj
    book_mode = BookMode(cli.engine)

    result = asyncio.run(book_mode.generate_diagram(description))
    print(result)


@app.command("hammer")
def book_hammer(
    ctx: typer.Context,
    enabled: bool = typer.Argument(..., help="Enable or disable coverage hammer")
):
    """Toggle the coverage hammer (anti-wrap continuation hint for self-study)."""
    cli: CLIContext = ctx.obj
    cli.state.coverage_hammer_on = enabled
    cli.save()
    print(f"Coverage hammer: {'ON' if cli.state.coverage_hammer_on else 'OFF'}")


@app.command("budget")
def output_budget(
    ctx: typer.Context,
    enabled: bool = typer.Argument(..., help="Enable or disable output budget addendum")
):
    """Toggle output budget addendum on book prompts."""
    cli: CLIContext = ctx.obj
    cli.state.output_budget_snippet_on = enabled
    cli.save()
    print(f"Output budget addendum: {'ON' if cli.state.output_budget_snippet_on else 'OFF'}")


@app.command("push")
def output_push(
    ctx: typer.Context,
    enabled: bool = typer.Argument(..., help="Enable or disable output pushing")
):
    """Toggle auto-extension within subtopic to hit min length."""
    cli: CLIContext = ctx.obj
    cli.state.output_push_on = enabled
    cli.save()
    print(f"Output push: {'ON' if cli.state.output_push_on else 'OFF'}")


@app.command("minchars")
def output_minchars(
    ctx: typer.Context,
    n: int = typer.Argument(..., help="Set minimal chars per chunk before moving on")
):
    """Set minimum characters per chunk."""
    cli: CLIContext = ctx.obj

    if n < 1000:
        print("Value too small; suggest >= 2500.")

    cli.state.output_min_chars = max(1000, n)
    cli.save()
    print(f"Output min chars: {cli.state.output_min_chars}")


@app.command("passes")
def output_passes(
    ctx: typer.Context,
    n: int = typer.Argument(..., help="Set max extension steps per chunk")
):
    """Set maximum extension passes per chunk."""
    cli: CLIContext = ctx.obj

    if n < 0 or n > 10:
        print("Unusual value; using within [0..10].")

    cli.state.output_push_max_passes = max(0, min(10, n))
    cli.save()
    print(f"Output push max passes: {cli.state.output_push_max_passes}")


@app.command("cont-mode")
def cont_mode(
    ctx: typer.Context,
    mode: str = typer.Argument(..., help="Set continuation mode (anchor/normal)")
):
    """Set continuation strategy."""
    cli: CLIContext = ctx.obj

    if mode.lower() in ["anchor", "normal"]:
        cli.state.continuation_mode = mode.lower()
        cli.save()
        print(f"Continuation mode: {cli.state.continuation_mode}")
    else:
        print("Usage: cont-mode [anchor|normal]")


@app.command("cont-anchor")
def cont_anchor(
    ctx: typer.Context,
    n: int = typer.Argument(..., help="Set anchor length in chars")
):
    """Set anchor length."""
    cli: CLIContext = ctx.obj

    if n < 50 or n > 2000:
        print("Choose a value between 50 and 2000.")
    else:
        cli.state.anchor_length = n
        cli.save()
        print(f"Anchor length: {cli.state.anchor_length}")


@app.command("repeat-warn")
def repeat_warn(
    ctx: typer.Context,
    enabled: bool = typer.Argument(..., help="Enable or disable repetition warning")
):
    """Toggle repetition warning."""
    cli: CLIContext = ctx.obj

    cli.state.repetition_warn = enabled
    cli.save()
    print(f"Repetition warning: {'ON' if cli.state.repetition_warn else 'OFF'}")


@app.command("repeat-thresh")
def repeat_thresh(
    ctx: typer.Context,
    threshold: float = typer.Argument(
        ..., help="Set repetition Jaccard threshold (0..1)"
    )
):
    """Set repetition threshold."""
    cli: CLIContext = ctx.obj

    if threshold <= 0 or threshold >= 1:
        print("Use a value between 0 and 1 (e.g., 0.35).")
    else:
        cli.state.repetition_threshold = threshold
        cli.save()
        print(f"Repetition threshold: {cli.state.repetition_threshold}")
