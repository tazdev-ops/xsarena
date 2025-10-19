"""Development and simulation commands for XSArena."""

import asyncio
from pathlib import Path

import typer

from ..core.v2_orchestrator.orchestrator import Orchestrator
from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset

app = typer.Typer(help="Development tools, automation, and fast offline simulation.")


@app.command("simulate")
def dev_simulate(
    subject: str = typer.Argument(..., help="Subject for the simulation"),
    length: str = typer.Option(
        "standard", "--length", help="Length preset: standard|long|very-long|max"
    ),
    span: str = typer.Option("medium", "--span", help="Span preset: medium|long|book"),
    script_path: str = typer.Option(
        None, "--script", "-s", help="Path to a script file with simulation responses"
    ),
):
    """Run a fast offline simulation using the null transport."""
    # Validate presets
    if length not in ["standard", "long", "very-long", "max"]:
        typer.echo(
            f"Error: Invalid length preset '{length}'. Choose from: standard, long, very-long, max"
        )
        raise typer.Exit(1)

    if span not in ["medium", "long", "book"]:
        typer.echo(
            f"Error: Invalid span preset '{span}'. Choose from: medium, long, book"
        )
        raise typer.Exit(1)

    # Prepare script for simulation
    script = None
    if script_path:
        script_file = Path(script_path)
        if not script_file.exists():
            typer.echo(f"Error: Script file not found at '{script_path}'")
            raise typer.Exit(1)

        # Read script from file - each line is a response
        with open(script_file, "r", encoding="utf-8") as f:
            script = [line.strip() for line in f if line.strip()]
    else:
        # Default simulation script
        script = [
            f"Introduction to {subject}. NEXT: [Continue with main concepts]",
            f"Main concepts of {subject}. NEXT: [Continue with applications]",
            f"Applications of {subject}. NEXT: [Continue with examples]",
            f"Examples of {subject}. NEXT: [Continue with conclusion]",
            f"Conclusion for {subject}. NEXT: [END]",
        ]

    typer.echo(f"Running simulation for '{subject}' with {len(script)} responses...")

    # Create RunSpecV2 for the simulation
    run_spec = RunSpecV2(
        subject=subject,
        length=LengthPreset(length),
        span=SpanPreset(span),
        overlays=["narrative", "no_bs"],  # Default overlays
        extra_note="",
        extra_files=[],
        out_path=f"./books/{subject.replace(' ', '_')}.final.md",
        profile="",
    )

    # Create orchestrator with null transport
    from ..core.backends import create_backend

    null_transport = create_backend("null", script=script)
    orchestrator = Orchestrator(transport=null_transport)

    # Run the simulation
    job_id = asyncio.run(orchestrator.run_spec(run_spec, backend_type="null"))

    typer.echo(f"Simulation completed! Job ID: {job_id}")
    typer.echo(f"Output saved to: {run_spec.out_path}")
