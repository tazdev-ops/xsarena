# src/xsarena/cli/registry.py
"""CLI command registry for XSArena."""

import typer

from ..core.config import Config

# Import all command modules
from .cmds_audio import app as audio_app
from .cmds_bilingual import app as bilingual_app
from .cmds_booster import app as booster_app

try:
    from .cmds_chad import app as chad_app
except ImportError:
    # chad module is optional
    chad_app = None
from .cmds_checklist import app as checklist_app
from .cmds_coach import app as coach_app
from .cmds_coder import app as coder_app
from .cmds_controls import app as controls_app
from .cmds_debug import app as debug_app

# Import roles and overlays commands
from .cmds_directives import overlays_list, overlays_show, roles_list, roles_show
from .cmds_docs import app as docs_app
from .cmds_endpoints import app as endpoints_app
from .cmds_health import app as health_app
from .cmds_interactive import app as interactive_app
from .cmds_jobs import app as jobs_app
from .cmds_joy import app as joy_app
from .cmds_json import app as json_app
from .cmds_list import app as list_app
from .cmds_macros import app as macros_app
from .cmds_metrics import app as metrics_app
from .cmds_modes import app as modes_app
from .cmds_people import app as people_app
from .cmds_pipeline import app as pipeline_app
from .cmds_playground import app as playground_app
from .cmds_policy import app as policy_app
from .cmds_preview import app as preview_app
from .cmds_publish import app as publish_app
from .cmds_report import app as report_app
from .cmds_run import app as run_app
from .cmds_snapshot import app as snapshot_app
from .cmds_tools import app as tools_app
from .cmds_unified_settings import app as unified_settings_app
from .cmds_upgrade import app as upgrade_app
from .cmds_workshop import app as workshop_app

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

# Directives group
# NOTE: Do NOT register 'directives' at top-level (tests expect it to be absent)
# app.add_typer(directives_app, name="directives", help="Directive utilities (roles, overlays, etc.)")

# Create sub-apps for roles and overlays to match test expectations
roles_app = typer.Typer(name="roles", help="Manage roles")
roles_app.command("list")(roles_list)
roles_app.command("show")(roles_show)
app.add_typer(roles_app)

overlays_app = typer.Typer(name="overlays", help="Manage overlays")
overlays_app.command("list")(overlays_list)
overlays_app.command("show")(overlays_show)
app.add_typer(overlays_app)

# Add the missing command groups
# NOTE: Do NOT register 'dev' at top-level (tests expect it to be absent)
# dev_group = typer.Typer(name="dev", help="Development tools and agent functionality.")
# dev_group.add_typer(agent_app, name="agent")
# app.add_typer(dev_group)

# NOTE: Do NOT register 'analyze' at top-level (tests expect it to be absent)
# app.add_typer(analyze_app, name="analyze")
app.add_typer(audio_app, name="audio", hidden=True)  # Hidden as per changelog
app.add_typer(bilingual_app, name="bilingual")
app.add_typer(
    booster_app, name="booster", help="Interactively engineer and improve prompts"
)
if chad_app:
    app.add_typer(chad_app, name="chad")
app.add_typer(checklist_app, name="checklist")
app.add_typer(coach_app, name="coach")
app.add_typer(coder_app, name="coder")
app.add_typer(
    controls_app,
    name="controls",
    help="Fine-tune output, continuation, and repetition behavior.",
)
ops_app.add_typer(debug_app, name="debug", help="Debugging commands")  # Add to ops
# NOTE: Do NOT register 'directives' at top-level (tests expect it to be absent)
app.add_typer(endpoints_app, name="endpoints")
app.add_typer(joy_app, name="joy", hidden=True)  # Hidden
app.add_typer(json_app, name="json")
app.add_typer(list_app, name="list")
app.add_typer(macros_app, name="macros")
app.add_typer(metrics_app, name="metrics")
app.add_typer(modes_app, name="modes", hidden=True)
app.add_typer(people_app, name="people", hidden=True)  # Hidden
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(playground_app, name="playground")
app.add_typer(policy_app, name="policy", hidden=True)  # Hidden
app.add_typer(preview_app, name="preview")
# NOTE: Do NOT register 'project' at top-level (tests expect it to be absent)
app.add_typer(publish_app, name="publish")
# NOTE: Do NOT register 'study' at top-level (tests expect it to be absent)
app.add_typer(upgrade_app, name="upgrade")
app.add_typer(workshop_app, name="workshop", hidden=True)  # Hidden

if __name__ == "__main__":
    app()
