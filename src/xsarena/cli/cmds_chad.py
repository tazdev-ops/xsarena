"""CLI commands for the Chad mode (evidence-based Q&A)."""

import asyncio
from pathlib import Path

import typer

from .context import CLIContext

app = typer.Typer(help="Direct, evidence-based Q&A")


def _get_chad_mode(cli):
    """Get ChadMode with error handling for missing dependencies."""
    try:
        from ..modes.chad import ChadMode
        return ChadMode(cli.engine)
    except ImportError:
        typer.echo(
            "Chad mode not available. Install required dependencies.",
            err=True,
        )
        raise typer.Exit(1)


@app.command("ask")
def chad_ask(
    ctx: typer.Context,
    question: str = typer.Argument(..., help="Question to answer"),
    context_file: str = typer.Option(
        "", "--context", "-c", help="Path to context file"
    ),
):
    """Answer a question based on evidence and context."""
    cli: CLIContext = ctx.obj
    mode = _get_chad_mode(cli)

    context = ""
    if context_file:
        context = Path(context_file).read_text(encoding="utf-8")

    async def run():
        result = await mode.answer_question(question, context)
        typer.echo(result)

    asyncio.run(run())


@app.command("batch")
def chad_batch(
    ctx: typer.Context,
    questions_file: str = typer.Argument(..., help="Path to questions file"),
    answers_file: str = typer.Argument(..., help="Path for answers output file"),
):
    """Process a batch of questions from a file and save answers."""
    cli: CLIContext = ctx.obj
    mode = _get_chad_mode(cli)

    async def run():
        result = await mode.batch_questions(questions_file, answers_file)
        typer.echo(result)

    asyncio.run(run())


@app.command("check")
def chad_check(
    ctx: typer.Context,
    claim: str = typer.Argument(..., help="Claim to fact-check"),
    evidence_file: str = typer.Argument(..., help="Path to evidence file"),
):
    """Check a claim against provided evidence."""
    cli: CLIContext = ctx.obj
    mode = _get_chad_mode(cli)

    evidence = Path(evidence_file).read_text(encoding="utf-8")

    async def run():
        result = await mode.evidence_check(claim, evidence)
        typer.echo(result)

    asyncio.run(run())


@app.command("sources")
def chad_sources(
    ctx: typer.Context,
    question: str = typer.Argument(..., help="Question to answer"),
    source_files: list[str] = typer.Argument(..., help="Paths to source files"),
):
    """Analyze multiple sources to answer a question."""
    cli: CLIContext = ctx.obj
    mode = _get_chad_mode(cli)

    sources = []
    for source_file in source_files:
        sources.append(Path(source_file).read_text(encoding="utf-8"))

    async def run():
        result = await mode.source_analysis(sources, question)
        typer.echo(result)

    asyncio.run(run())


@app.command("fact-check")
def chad_fact_check(
    ctx: typer.Context,
    statement: str = typer.Argument(..., help="Statement to fact-check"),
):
    """Fact-check a given statement."""
    cli: CLIContext = ctx.obj
    mode = _get_chad_mode(cli)

    async def run():
        result = await mode.fact_check(statement)
        typer.echo(result)

    asyncio.run(run())


@app.command("summarize")
def chad_summarize(
    ctx: typer.Context,
    evidence_files: list[str] = typer.Argument(..., help="Paths to evidence files"),
):
    """Summarize a list of evidence points."""
    cli: CLIContext = ctx.obj
    mode = _get_chad_mode(cli)

    evidence_list = []
    for evidence_file in evidence_files:
        evidence_list.append(Path(evidence_file).read_text(encoding="utf-8"))

    async def run():
        result = await mode.summarize_evidence(evidence_list)
        typer.echo(result)

    asyncio.run(run())
