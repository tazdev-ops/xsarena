# src/xsarena/cli/cmds_interactive.py
import typer

app = typer.Typer(help="Interactive REPL (modular)")

@app.command("start")
def start():
    """Start the interactive REPL."""
    typer.echo("ℹ️  Interactive REPL is deprecated. Use 'xsarena run book' for canonical runs.")
    typer.echo("For project management, use 'xsarena project ...' commands.")
    typer.echo("For continued writing, use 'xsarena continue start ...'.")
    typer.echo("See documentation for the recommended workflow.")