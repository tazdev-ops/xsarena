#!/usr/bin/env python3
import re

import typer

app = typer.Typer(help="Interactive wizard to run Z2H")


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


@app.command("z2h")
def wizard_z2h():
    subject = typer.prompt("Subject")
    audience = typer.prompt("Audience (e.g., beginners, MSc candidates)", default="beginners")
    tone = typer.prompt("Tone (e.g., clear, no-BS, narrative)", default="clear, no-BS, narrative")
    minc = typer.prompt("Min chars per chunk (~3000 default)", default="3000")
    maxc = typer.prompt("Max chunks (0=unlimited)", default="8")
    aids = typer.prompt(
        "Aids (comma-separated: cram,flashcards,glossary,index,audio)", default="cram,flashcards,glossary,index"
    )

    # create a small playbook override and submit
    system_text = f"""English only. Teach-before-use; define terms on first use (bold + 1 line).
Narrative for {audience}; tone: {tone}. Short vignette; 2–3 quick checks; pitfalls per section.
No early wrap-up; continue exactly where you left off."""
    params = {
        "subject": subject,
        "system_text": system_text,
        "max_chunks": int(maxc),
        "continuation": {"minChars": int(minc), "pushPasses": 1, "repeatWarn": True},
        "aids": [a.strip() for a in aids.split(",") if a.strip()],
    }
    # reuse your JobRunner submit via cmds_jobs.z2h internally:
    from ..core.jobs2 import JobRunner
    from ..core.playbooks import load_playbook, merge_defaults

    defaults = {}
    jrunner = JobRunner(defaults)
    pb = load_playbook("playbooks/z2h.yml")
    merged = merge_defaults(pb, defaults, params)
    job_id = jrunner.submit(merged, params)
    typer.echo(f"[wizard] Submitted: {job_id}")
