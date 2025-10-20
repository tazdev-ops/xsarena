# src/xsarena/cli/registry.py
"""CLI command registry for XSArena."""

import typer

from .cmds_adapt import app as adapt_app

# Import all command modules
from .cmds_agent import app as agent_app
from .cmds_analyze import (
    continuity_cmd,
    coverage_cmd,
    readtime_cmd,
    secrets_cmd,
    style_lint_cmd,
)
from .cmds_audio import app as audio_app
from .cmds_booster import app as booster_app
from .cmds_chad import app as chad_app
from .cmds_checklist import app as checklist_app
from .cmds_coach import app as coach_app
from .cmds_debug import app as debug_app
from .cmds_dev import dev_simulate
from .cmds_directives import app as directives_app
from .cmds_docs import app as docs_app
from .cmds_doctor import app as doctor_app
from .cmds_endpoints import app as endpoints_app
from .cmds_health import app as health_app
from .cmds_interactive import app as interactive_app
from .cmds_jobs import app as jobs_app
from .cmds_joy import app as joy_app
from .cmds_json import app as json_app
from .cmds_list import app as list_app
from .cmds_macros import app as macros_app
from .cmds_metrics import app as metrics_app
from .cmds_people import app as people_app
from .cmds_pipeline import app as pipeline_app
from .cmds_playground import app as playground_app
from .cmds_preview import app as preview_app
from .cmds_project import app as project_app
from .cmds_publish import app as publish_app
from .cmds_run import app as run_app
from .cmds_snapshot import app as snapshot_app
from .cmds_study import app as study_app
from .cmds_tools import app as tools_app
from .cmds_tools import fun_tldr
from .cmds_unified_settings import app as unified_settings_app
from .cmds_upgrade import app as upgrade_app
from .cmds_workshop import app as workshop_app
from .service import app as service_app

# --- Main App ---
app = typer.Typer(help="XSArena — AI-powered writing and coding studio")

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
author_app.add_typer(workshop_app, name="workshop")
author_app.add_typer(preview_app, name="preview")

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

analyze_app = typer.Typer(
    name="analyze", help="Analysis, reporting, and evidence-based tools."
)
analyze_app.command("coverage")(coverage_cmd)
analyze_app.command("style-lint")(style_lint_cmd)
analyze_app.command("secrets")(secrets_cmd)
analyze_app.command("continuity")(continuity_cmd)
analyze_app.command("readtime")(readtime_cmd)
analyze_app.add_typer(chad_app, name="chad")
app.add_typer(analyze_app)

study_group = typer.Typer(
    name="study", help="Study aids, learning tools, and practice drills."
)
study_group.add_typer(study_app, name="generate")
study_group.add_typer(coach_app, name="coach")
study_group.add_typer(joy_app, name="joy")
app.add_typer(study_group)

dev_app_group = typer.Typer(
    name="dev", help="Coding agent, simulation, and automation pipelines."
)
dev_app_group.add_typer(agent_app, name="agent")
dev_app_group.add_typer(pipeline_app, name="pipeline")
dev_app_group.command("simulate")(dev_simulate)
app.add_typer(dev_app_group)

from .cmds_settings import app as config_app

ops_app = typer.Typer(
    name="ops", help="System health, jobs, services, and configuration."
)
ops_app.add_typer(service_app, name="service")
ops_app.add_typer(jobs_app, name="jobs")
ops_app.add_typer(doctor_app, name="doctor")
ops_app.add_typer(
    health_app,
    name="health",
    help="System health, maintenance, and self-healing operations",
)
ops_app.add_typer(snapshot_app, name="snapshot")

ops_app.add_typer(metrics_app, name="metrics")
ops_app.add_typer(upgrade_app, name="upgrade")
ops_app.add_typer(adapt_app, name="adapt", help="Adaptive inspection and safe fixes")
ops_app.add_typer(
    config_app, name="config", help="Configuration and backend management"
)
app.add_typer(ops_app)

project_app_group = typer.Typer(
    name="project", help="Project management and initialization."
)
project_app_group.add_typer(project_app)
app.add_typer(project_app_group)

directives_group = typer.Typer(
    name="directives", help="Manage directives, profiles, and endpoints."
)
directives_group.add_typer(directives_app, name="index")
directives_group.add_typer(booster_app, name="booster")
directives_group.add_typer(endpoints_app, name="endpoints")
directives_group.add_typer(list_app, name="list")
app.add_typer(directives_group)

# --- Additional Semantic Groups ---
utilities_group = typer.Typer(name="utils", help="General utility commands.")

utilities_group.add_typer(macros_app, name="macros", help="Manage CLI command macros.")
utilities_group.add_typer(
    json_app, name="json", help="JSON validation and processing tools"
)
utilities_group.add_typer(
    tools_app,
    name="tools",
    help="Utility tools like chapter export and checklist extraction.",
)
utilities_group.command("tldr")(fun_tldr)
utilities_group.add_typer(
    people_app, name="people", help="Roleplay engine.", hidden=True
)
utilities_group.add_typer(
    publish_app, name="publish", help="Publishing tools (PDF, EPUB, web)", hidden=True
)
utilities_group.add_typer(
    audio_app, name="audio", help="Audio generation (TTS, podcasts)", hidden=True
)
utilities_group.add_typer(
    debug_app, name="debug", help="Debugging commands", hidden=True
)
utilities_group.add_typer(
    checklist_app,
    name="checklist",
    help="Implementation checklist and verification",
    hidden=True,
)
utilities_group.add_typer(
    playground_app,
    name="playground",
    help="Prompt composition and sampling playground",
)

app.add_typer(utilities_group)

# Documentation group
app.add_typer(docs_app, name="docs", help="Documentation generation commands")

if __name__ == "__main__":
    app()
