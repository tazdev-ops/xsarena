# src/xsarena/cli/registry.py
"""CLI command registry for XSArena."""

import typer

from ..core.config import Config

# Import all command modules
from .cmds_docs import app as docs_app
from .cmds_health import app as health_app
from .cmds_interactive import app as interactive_app
from .cmds_jobs import app as jobs_app
from .cmds_report import app as report_app
from .cmds_run import app as run_app
from .cmds_snapshot import app as snapshot_app
from .cmds_tools import app as tools_app
from .cmds_unified_settings import app as unified_settings_app

# --- Global CLI context init (ensures ctx.obj is set for all commands)
from .context import CLIContext
from .service import app as service_app

# --- Main App ---
app = typer.Typer(help="XSArena — AI-powered writing and coding studio")


# --- Global CLI context init (ensures ctx.obj is set for all commands)
@app.callback()
def _init_ctx(
    ctx: typer.Context,
    backend: str = typer.Option(
        None, "--backend", help="Override backend for this invocation"
    ),
    model: str = typer.Option(
        None, "--model", help="Override model for this invocation"
    ),
    base_url: str = typer.Option(None, "--base-url", help="Override bridge base URL"),
):
    cfg_over = None
    if any([backend, model, base_url]):
        cfg_over = Config(
            backend=backend or "bridge",
            model=model or "default",
            base_url=base_url or "http://127.0.0.1:5102/v1",
        )
    ctx.obj = CLIContext.load(cfg=cfg_over)


# --- Essential Top-Level Commands ---
app.add_typer(run_app, name="run", help="Run a book or recipe in authoring mode")
app.add_typer(interactive_app, name="interactive", help="Interactive authoring session")
app.add_typer(
    unified_settings_app,
    name="settings",
    help="Unified settings interface (configuration + controls)",
)

# --- Semantic Command Groups ---
author_app = typer.Typer(name="author", help="Core content creation workflows.")

# Add post-process tools as a subgroup under author
from .cmds_tools import export_chapters_cmd, extract_checklists_cmd

post_process_app = typer.Typer(
    name="post-process", help="Post-processing tools (aliases to utils tools)"
)
post_process_app.command("export-chapters")(export_chapters_cmd)
post_process_app.command("extract-checklists")(extract_checklists_cmd)
author_app.add_typer(post_process_app, name="post-process")

app.add_typer(author_app)

# Add authoring commands directly to the author app
from .cmds_authoring import (
    ingest_ack,
    ingest_run,
    ingest_style,
    ingest_synth,
    lossless_break_paragraphs,
    lossless_enhance_structure,
    lossless_improve_flow,
    lossless_ingest,
    lossless_rewrite,
    lossless_run,
    style_narrative,
    style_nobs,
    style_reading,
    style_show,
)

author_app.command("ingest-ack")(ingest_ack)
author_app.command("ingest-synth")(ingest_synth)
author_app.command("ingest-style")(ingest_style)
author_app.command("ingest-run")(ingest_run)
author_app.command("lossless-ingest")(lossless_ingest)
author_app.command("lossless-rewrite")(lossless_rewrite)
author_app.command("lossless-run")(lossless_run)
author_app.command("lossless-improve-flow")(lossless_improve_flow)
author_app.command("lossless-break-paragraphs")(lossless_break_paragraphs)
author_app.command("lossless-enhance-structure")(lossless_enhance_structure)
author_app.command("style-narrative")(style_narrative)
author_app.command("style-nobs")(style_nobs)
author_app.command("style-reading")(style_reading)
author_app.command("style-show")(style_show)

from .cmds_settings import app as config_app

ops_app = typer.Typer(
    name="ops", help="System health, jobs, services, and configuration."
)
ops_app.add_typer(service_app, name="service")
ops_app.add_typer(jobs_app, name="jobs")
ops_app.add_typer(
    health_app,
    name="health",
    help="System health, maintenance, and self-healing operations",
)
ops_app.add_typer(snapshot_app, name="snapshot")
ops_app.add_typer(
    config_app, name="config", help="Configuration and backend management"
)
# Import and register the new command groups
from .cmds_handoff import app as handoff_app
from .cmds_orders import app as orders_app
from .cmds_report import app as report_app

app.add_typer(report_app, name="report", help="Create diagnostic reports")
ops_app.add_typer(handoff_app, name="handoff", help="Prepare higher-AI handoffs")
ops_app.add_typer(orders_app, name="orders", help="Manage ONE ORDER log")

app.add_typer(ops_app)

# --- Additional Semantic Groups ---
utilities_group = typer.Typer(name="utils", help="General utility commands.")

utilities_group.add_typer(
    tools_app,
    name="tools",
    help="Utility tools like chapter export and checklist extraction.",
)

app.add_typer(utilities_group)

# Documentation group
app.add_typer(docs_app, name="docs", help="Documentation generation commands")

if __name__ == "__main__":
    app()
