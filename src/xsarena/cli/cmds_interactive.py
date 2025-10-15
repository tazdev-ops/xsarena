# src/xsarena/cli/cmds_interactive.py
import typer

app = typer.Typer(help="Interactive REPL (modular)")

@app.command("start")
def start():
    """Start the modular interactive REPL."""
    typer.echo("ERROR: The modular REPL is not fully implemented and cannot be started.")
    typer.echo("A required 'state' object is missing from the function call specified in the original order.")