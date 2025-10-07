"""Main CLI entry point for XSArena."""

import typer

from .cmds_audio import app as audio_app
from .cmds_backend import app as backend_app

# Import mode handlers
from .cmds_book import app as book_app
from .cmds_coach import app as coach_app
from .cmds_coder import app as coder_app
from .cmds_debug import app as debug_app
from .cmds_diagram import app as diagram_app
from .cmds_doctor import app as doctor_app
from .cmds_fun import app as fun_app
from .cmds_import import app as import_app
from .cmds_init import app as init_app
from .cmds_jobs import app as jobs_app
from .cmds_joy import app as joy_app
from .cmds_lossless import app as lossless_app
from .cmds_modes import app as modes_app
from .cmds_pipeline import app as pipeline_app
from .cmds_publish import app as publish_app
from .cmds_quality import app as quality_app
from .cmds_roleplay import app as rp_app
from .cmds_serve import app as serve_app
from .cmds_snapshot import app as snapshot_app
from .cmds_style import app as style_app
from .cmds_summary import app as summary_app
from .cmds_surprise import app as surprise_app
from .cmds_templates import app as templates_app
from .cmds_wizard import app as wizard_app
from .cmds_zen import app as zen_app
from .service import app as service_app

app = typer.Typer()

# Add subcommands for each mode
app.add_typer(book_app, name="book", help="Book authoring commands")
app.add_typer(lossless_app, name="lossless", help="Lossless text processing commands")
app.add_typer(backend_app, name="backend", help="Backend configuration commands")
app.add_typer(debug_app, name="debug", help="Debugging commands")
app.add_typer(modes_app, name="mode", help="Mode toggles and settings")
app.add_typer(service_app, name="service", help="Service management (start servers)")
app.add_typer(pipeline_app, name="pipeline", help="Pipeline runner (fix → test → format → commit)")
app.add_typer(jobs_app, name="jobs", help="Job management commands")
app.add_typer(doctor_app, name="doctor", help="Health checks and a synthetic Z2H smoke test")
app.add_typer(serve_app, name="serve", help="Local web preview")
app.add_typer(publish_app, name="publish", help="Export books to EPUB/PDF")
app.add_typer(audio_app, name="audio", help="Convert EPUB to audiobook (Edge TTS or external tool)")
app.add_typer(quality_app, name="quality", help="Quality scoring & auto-rewrite")
app.add_typer(import_app, name="import", help="Import PDF/DOCX/MD → Markdown in sources/")
app.add_typer(init_app, name="init", help="Initialize project scaffolding")
app.add_typer(style_app, name="style", help="Capture/apply writing styles")
app.add_typer(wizard_app, name="wizard", help="Interactive scaffolding")
app.add_typer(diagram_app, name="diagram", help="Generate diagrams from Mermaid")
app.add_typer(summary_app, name="summary", help="Job metrics summary")
app.add_typer(templates_app, name="templates", help="Templates registry")
app.add_typer(snapshot_app, name="snapshot", help="Snapshot utilities (create, diff, share)")
app.add_typer(coder_app, name="coder", help="Advanced coding session with tickets, patches, and git integration")
app.add_typer(joy_app, name="joy", help="Daily joy, streaks, achievements")
app.add_typer(coach_app, name="coach", help="Coach drills and Boss mini-exams")
app.add_typer(fun_app, name="fun", help="ELI5, stories, personas, toggles")
app.add_typer(zen_app, name="zen", help="Zen focus sessions")
app.add_typer(surprise_app, name="surprise", help="Surprise me")
app.add_typer(rp_app, name="rp", help="Roleplay sessions (personas, say, boundaries, model, export)")


@app.command("z2h")
def z2h_top(
    subject: str,
    out: str = typer.Option(None, "--out"),
    max_chunks: int = typer.Option(8, "--max"),
    min_chars: int = typer.Option(3000, "--min"),
):
    """Zero-to-Hero: Create comprehensive content on a topic"""
    from .cmds_jobs import z2h as z2h_cmd

    z2h_cmd(subject, out, max_chunks, min_chars)


@app.command("z2h-list")
def z2h_list_top(
    subjects: str, max_chunks: int = typer.Option(8, "--max"), min_chars: int = typer.Option(3000, "--min")
):
    """Process multiple subjects in a list"""
    from .cmds_jobs import z2h_list as z2h_list_cmd

    z2h_list_cmd(subjects, max_chunks, min_chars)


@app.callback()
def main(
    backend: str = typer.Option("bridge", help="Backend to use (bridge or openrouter)"),
    model: str = typer.Option("default", help="Model to use"),
    window: int = typer.Option(100, help="Window size for history"),
):
    """
    XSArena - AI-powered writing and coding studio
    """
    # Store configuration in a global context or pass to commands
    pass


def run():
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()
