"""Main CLI entry point for XSArena."""

import typer

from .cmds_backend import app as backend_app
from .context import CLIContext
from ..core.config import Config

# Import mode handlers
from .cmds_book import app as book_app
from .cmds_debug import app as debug_app
from .cmds_lossless import app as lossless_app
from .cmds_modes import app as modes_app
from .cmds_mixer import app as mix_app
from .cmds_fast import app as fast_app
from .cmds_jobs import app as jobs_app
from .cmds_preview import app as preview_app
from .cmds_publish import app as publish_app
from .cmds_audio import app as audio_app
from .cmds_snapshot import app as snapshot_app
from .cmds_metrics import app as metrics_app
from .cmds_pipeline import app as pipeline_app

from .cmds_config import app as config_app
from .cmds_continue import app as continue_app
from .cmds_fix import app as fix_app
from .cmds_clean import app as clean_app
from .cmds_plan import app as plan_app
from .cmds_quick import app as quick_app
from .cmds_run import app as run_app
from .cmds_report import app as report_app
from .cmds_adapt import app as adapt_app
from .cmds_boot import app as boot_app
from .service import app as service_app

app = typer.Typer(help="XSArena — AI-powered writing and coding studio")

# Add subcommands for each mode
app.add_typer(book_app, name="book", help="Book authoring commands")
app.add_typer(lossless_app, name="lossless", help="Lossless text processing commands")
app.add_typer(backend_app, name="backend", help="Backend configuration commands")
app.add_typer(debug_app, name="debug", help="Debugging commands")
app.add_typer(modes_app, name="mode", help="Mode toggles and settings")
app.add_typer(mix_app, name="mix", help="Mode mixer with prompt preview/edit")
app.add_typer(fast_app, name="fast", help="Fast headless mode with standardized parameters")
app.add_typer(jobs_app, name="jobs", help="Job execution (recipes, book generation)")
app.add_typer(preview_app, name="preview", help="Preview prompt + style sample for recipes")
app.add_typer(publish_app, name="publish", help="Publishing tools (PDF, EPUB, web)")
app.add_typer(audio_app, name="audio", help="Audio generation (TTS, podcasts)")
app.add_typer(snapshot_app, name="snapshot", help="Snapshot tools with chunking and redaction")
app.add_typer(metrics_app, name="metrics", help="Metrics and observability")
app.add_typer(service_app, name="service", help="Service management (start servers)")
app.add_typer(
    pipeline_app, name="pipeline", help="Pipeline runner (fix → test → format → commit)"
)

app.add_typer(continue_app, name="continue", help="Continue from file tail (anchor)")
app.add_typer(fix_app, name="fix", help="Self-heal configuration/state")
app.add_typer(config_app, name="config", help="Configuration management")
app.add_typer(clean_app, name="clean", help="Cleanup (TTL-based sweeper)")
app.add_typer(plan_app, name="plan", help="Plan from seeds in editor, then run a long book")
app.add_typer(quick_app, name="quick", help="Quick launcher (wait for capture, profiles)")
app.add_typer(run_app, name="run", help="Unified runner (book/continue)")
app.add_typer(report_app, name="report", help="Create a redacted report bundle")
app.add_typer(adapt_app, name="adapt", help="Adaptive inspection and safe fixes")
app.add_typer(boot_app, name="boot", help="Startup reader (startup.yml)")


@app.callback()
def main(
    ctx: typer.Context,
    backend: str = typer.Option("bridge", help="Backend to use (bridge or openrouter)"),
    model: str = typer.Option("default", help="Model to use"),
    window: int = typer.Option(100, help="Window size for history"),
):
    """
    XSArena - AI-powered writing and coding studio
    
    XSArena uses Bridge-first architecture by default. This means it connects to a local
    bridge server that relays requests to the actual LMArena backend through your browser.
    """
    # Build persistent CLI context and stash on typer context
    cfg = Config(backend=backend, model=model, window_size=window)
    cli_ctx = CLIContext.load(cfg)
    # Persist immediate overrides (so switches via flags are remembered)
    cli_ctx.state.backend = backend
    cli_ctx.state.model = model
    cli_ctx.state.window_size = window
    cli_ctx.save()
    ctx.obj = cli_ctx


@app.command("version")
def _version():
    from .. import __version__
    typer.echo(f"XSArena v{__version__}")


def run():
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()
