from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
import yaml

from ..core.jobs2_runner import JobRunner
from ..core.prompt import compose_prompt
from ..core.specs import DEFAULT_PROFILES, LENGTH_PRESETS, SPAN_PRESETS
from .context import CLIContext

app = typer.Typer(
    help="Plan from rough seeds in your editor, then run a long, dense book."
)

_PLANNER_PROMPT = """You are an editorial planner for a long-form self-study manual.
The user will provide rough seeds (topics/notes). Your job:
- subject: one-line final title (concise, specific)
- goal: 3–5 sentences (scope, depth, audience, exclusions)
- focus: 5–8 bullets (what to emphasize/avoid)
- outline: 10–16 top-level sections; each item has:
    - title: short section heading
    - cover: 2–4 bullets of what to cover
Return STRICT YAML only with keys: subject, goal, focus, outline. No code fences, no commentary.

Seeds:
<<<SEEDS
{seeds}
SEEDS>>>"""


def _slugify(s: str) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "book"


def _editor_seed() -> str:
    return (
        "# Write your rough seeds below. One item per line; keep it messy. Save and close to proceed.\n"
        "# Example:\n"
        "# 1) cicero (speeches)\n"
        "# 2) roman republic history (1st BCE)\n"
        "# 3) political history (theories for understanding)\n"
        "# 4) relevant social sciences lenses\n"
        "# 5) roman law/constitution (relevant bits)\n\n"
    )


@app.command("start")
def plan_start(
    ctx: typer.Context,
    subject: Optional[str] = typer.Option(
        None, "--subject", "-s", help="Final subject/title (leave empty to infer)"
    ),
    profile: str = typer.Option(
        "",
        "--profile",
        help="Preset: clinical-masters|elections-focus|compressed-handbook|pop-explainer|bilingual-pairs",
    ),
    length: str = typer.Option(
        "long", "--length", help="Per-message length: standard|long|very-long|max"
    ),
    span: str = typer.Option("book", "--span", help="Total span: medium|long|book"),
    out_path: str = typer.Option(
        "", "--out", "-o", help="Output path (defaults to books/finals/<slug>.final.md)"
    ),
    extra_file: List[str] = typer.Option(
        [],
        "--extra-file",
        "-E",
        help="Append file(s) to system prompt (e.g., directives/_rules/rules.merged.md)",
    ),
    wait: bool = typer.Option(
        True,
        "--wait/--no-wait",
        help="Prompt to wait for browser capture before starting",
    ),
):
    """DEPRECATED: Use 'xsarena run from-plan' instead."""
    typer.echo("⚠️  DEPRECATED: Use 'xsarena run from-plan' instead.")
    
    # Map plan parameters to run command
    typer.echo(f"Would run plan job for: {subject or 'Untitled Project'}")
    typer.echo("Please use 'xsarena run from-plan' with appropriate parameters instead.")
