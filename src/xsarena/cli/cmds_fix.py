from __future__ import annotations
import typer
from .context import CLIContext

app = typer.Typer(help="Self-heal common configuration/state issues")

@app.command("run")
def fix_run(ctx: typer.Context):
    cli: CLIContext = ctx.obj
    notes = cli.fix()
    typer.echo("=== Fix summary ===")
    for n in notes:
        typer.echo(f"  - {n}")
    typer.echo("Done.")