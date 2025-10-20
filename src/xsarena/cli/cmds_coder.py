"""CLI commands for the Coder mode."""
import asyncio

import typer

from ..modes.coder import CoderMode
from .context import CLIContext

app = typer.Typer(help="Coding assistance tools")


@app.command("edit")
def coder_edit(
    ctx: typer.Context,
    file_path: str = typer.Argument(..., help="Path to file to edit"),
    instruction: str = typer.Argument(..., help="Instruction for code modification"),
    line_start: int = typer.Option(None, "--start", "-s", help="Start line for edit"),
    line_end: int = typer.Option(None, "--end", "-e", help="End line for edit"),
):
    """Edit code in a file based on instruction."""
    cli: CLIContext = ctx.obj
    mode = CoderMode(cli.engine)

    async def run():
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        result = await mode.edit_code(content, instruction, line_start, line_end)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(result)
        typer.echo(f"Code edited in {file_path}")

    asyncio.run(run())


@app.command("review")
def coder_review(
    ctx: typer.Context,
    file_path: str = typer.Argument(..., help="Path to file to review"),
):
    """Review code and provide feedback."""
    cli: CLIContext = ctx.obj
    mode = CoderMode(cli.engine)

    async def run():
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        result = await mode.review_code(content)
        typer.echo(result)

    asyncio.run(run())


@app.command("explain")
def coder_explain(
    ctx: typer.Context,
    file_path: str = typer.Argument(..., help="Path to file to explain"),
):
    """Explain code functionality."""
    cli: CLIContext = ctx.obj
    mode = CoderMode(cli.engine)

    async def run():
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        result = await mode.explain_code(content)
        typer.echo(result)

    asyncio.run(run())
