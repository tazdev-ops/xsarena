"""CLI commands for the Policy mode."""

import asyncio
from pathlib import Path

import typer

from ..modes.policy import PolicyMode
from .context import CLIContext

app = typer.Typer(help="Policy analysis and generation tools")


@app.command("generate")
def policy_generate(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic for the policy"),
    requirements_file: str = typer.Option(
        "", "--requirements", "-r", help="Path to requirements file"
    ),
):
    """Generate a policy document from a topic and requirements."""
    cli: CLIContext = ctx.obj
    mode = PolicyMode(cli.engine)

    requirements = ""
    if requirements_file:
        requirements = Path(requirements_file).read_text(encoding="utf-8")

    async def run():
        result = await mode.generate_from_topic(topic, requirements)
        print(result)

    asyncio.run(run())


@app.command("analyze")
def policy_analyze(
    ctx: typer.Context,
    policy_file: str = typer.Argument(..., help="Path to policy document"),
    evidence_files: list[str] = typer.Argument(..., help="Paths to evidence files"),
):
    """Analyze policy compliance against evidence files."""
    cli: CLIContext = ctx.obj
    mode = PolicyMode(cli.engine)

    policy = Path(policy_file).read_text(encoding="utf-8")
    evidence_texts = []
    for evidence_file in evidence_files:
        evidence_texts.append(Path(evidence_file).read_text(encoding="utf-8"))

    async def run():
        result = await mode.analyze_compliance(policy, evidence_texts)
        print(result)

    asyncio.run(run())


@app.command("score")
def policy_score(
    ctx: typer.Context,
    policy_file: str = typer.Argument(..., help="Path to policy document"),
    evidence_files: list[str] = typer.Argument(..., help="Paths to evidence files"),
):
    """Score policy compliance against evidence files."""
    cli: CLIContext = ctx.obj
    mode = PolicyMode(cli.engine)

    policy = Path(policy_file).read_text(encoding="utf-8")
    evidence_texts = []
    for evidence_file in evidence_files:
        evidence_texts.append(Path(evidence_file).read_text(encoding="utf-8"))

    async def run():
        result = await mode.score_compliance(policy, evidence_texts)
        print(result)

    asyncio.run(run())


@app.command("gaps")
def policy_gaps(
    ctx: typer.Context,
    policy_file: str = typer.Argument(..., help="Path to policy document"),
    requirements_file: str = typer.Argument(..., help="Path to requirements file"),
):
    """Analyze gaps between policy and requirements."""
    cli: CLIContext = ctx.obj
    mode = PolicyMode(cli.engine)

    policy = Path(policy_file).read_text(encoding="utf-8")
    requirements = Path(requirements_file).read_text(encoding="utf-8")

    async def run():
        result = await mode.gap_analysis(policy, requirements)
        print(result)

    asyncio.run(run())


@app.command("checklist")
def policy_checklist(
    ctx: typer.Context,
    policy_file: str = typer.Argument(..., help="Path to policy document"),
):
    """Generate an implementation checklist for the policy."""
    cli: CLIContext = ctx.obj
    mode = PolicyMode(cli.engine)

    policy = Path(policy_file).read_text(encoding="utf-8")

    async def run():
        result = await mode.implementation_checklist(policy)
        print(result)

    asyncio.run(run())
