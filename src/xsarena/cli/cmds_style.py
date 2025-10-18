import typer

from .context import CLIContext

app = typer.Typer(help="Apply style and pedagogy overlays.")


@app.command("narrative")
def style_narrative(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Enable or disable the narrative/pedagogy overlay for the session."""
    cli: CLIContext = ctx.obj
    if enable:
        cli.state.overlays_active.add("narrative")
    else:
        cli.state.overlays_active.discard("narrative")
    cli.save()
    status = "ON" if enable else "OFF"
    typer.echo(f"Narrative overlay set to: {status}")


@app.command("nobs")
def style_nobs(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Enable or disable the no-bullshit (no-bs) language overlay."""
    cli: CLIContext = ctx.obj
    if enable:
        cli.state.overlays_active.add("no_bs")
    else:
        cli.state.overlays_active.discard("no_bs")
    cli.save()
    status = "ON" if enable else "OFF"
    typer.echo(f"No-BS overlay set to: {status}")


@app.command("reading")
def style_reading(
    ctx: typer.Context,
    enable: bool = typer.Argument(
        ..., help="Enable or disable the reading overlay (on|off)"
    ),
):
    """Enable or disable the further reading overlay for the session."""
    cli: CLIContext = ctx.obj
    if isinstance(enable, str):
        enable = enable.lower() == "on"

    cli.state.reading_overlay_on = enable
    cli.save()
    status = "ON" if enable else "OFF"
    typer.echo(f"Reading overlay set to: {status}")


@app.command("show")
def style_show(ctx: typer.Context):
    """Show currently active overlays."""
    cli: CLIContext = ctx.obj
    active_overlays = list(cli.state.overlays_active)
    reading_status = "ON" if cli.state.reading_overlay_on else "OFF"

    if active_overlays:
        typer.echo(f"Active overlays: {', '.join(active_overlays)}")
    else:
        typer.echo("No overlays currently active")

    typer.echo(f"Reading overlay: {reading_status}")
