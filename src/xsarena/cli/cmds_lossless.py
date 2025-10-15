"""Lossless mode CLI commands for XSArena."""

import asyncio
import typer

from .context import CLIContext
from ..modes.lossless import LosslessMode

app = typer.Typer()


@app.command("ingest")
def lossless_ingest(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to ingest and synthesize")
):
    """Ingest and synthesize information from text."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.ingest_synth(text))
    print(result)


@app.command("rewrite")
def lossless_rewrite(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to rewrite while preserving meaning")
):
    """Rewrite text while preserving all meaning."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.rewrite_lossless(text))
    print(result)


@app.command("run")
def lossless_run(
    ctx: typer.Context,
    text: str = typer.Argument(
        ..., help="Text to process with comprehensive lossless processing"
    )
):
    """Perform a comprehensive lossless processing run."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.lossless_run(text))
    print(result)


@app.command("improve-flow")
def lossless_improve_flow(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to improve flow for")
):
    """Improve the flow and transitions in text."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.improve_flow(text))
    print(result)


@app.command("break-paragraphs")
def lossless_break_paragraphs(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to break into more readable paragraphs")
):
    """Break dense paragraphs into more readable chunks."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.break_paragraphs(text))
    print(result)


@app.command("enhance-structure")
def lossless_enhance_structure(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to enhance with better structure")
):
    """Enhance text structure with appropriate headings and formatting."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.enhance_structure(text))
    print(result)
