"""Interactive CLI commands for XSArena."""

from __future__ import annotations

import asyncio

import typer

from .interactive_session import start_interactive_session

app = typer.Typer(
    help="Interactive cockpit (REPL-lite) with live steering and job control"
)


@app.command("start")
def interactive_start(ctx: typer.Context):
    """Start the interactive cockpit session."""
    cli = ctx.obj

    # Run the async function
    asyncio.run(start_interactive_session(cli))
