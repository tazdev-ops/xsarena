from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import asyncio
import typer
import yaml

from .context import CLIContext
from ..core.prompt import compose_prompt
from ..core.jobs2_runner import JobRunner

app = typer.Typer(help="Plan from rough seeds in your editor, then run a long, dense book.")

# Descriptive presets (no numbers shown to user)
LENGTH_PRESETS = {
    "standard": {"min": 4200, "passes": 1},
    "long": {"min": 5800, "passes": 3},
    "very-long": {"min": 6200, "passes": 4},
    "max": {"min": 6800, "passes": 5},
}
SPAN_PRESETS = {"medium": 12, "long": 24, "book": 40}

PROFILES = {
    "clinical-masters": {
        "overlays": ["narrative", "no_bs"],
        "extra": ("Clinical focus: teach‑before‑use; define clinical terms in plain English; "
                  "cover models of psychopathology, assessment validity, case formulation, mechanisms, "
                  "evidence‑based practice (evidence + expertise + patient values), outcomes/effect sizes; "
                  "neutral narrative; avoid slogans/keywords; do not disclose protected test items.")
    },
    "elections-focus": {
        "overlays": ["narrative", "no_bs"],
        "extra": ("Focus: treat elections as hinge points to explain coalitions, party systems, and institutional change; "
                  "avoid seat lists unless they explain mechanism; dense narrative; no bullet walls.")
    },
    "compressed-handbook": {"overlays": ["compressed", "no_bs"], "extra": "Compressed narrative handbook; minimal headings; no bullet walls; no slogans."},
    "pop-explainer": {"overlays": ["no_bs"], "extra": "Accessible narrative explainer for general audiences; neutral tone; no hype."},
    "bilingual-pairs": {"overlays": ["narrative", "no_bs", "bilingual"], "extra": "Output sections as EN/FA pairs with identical structure; translate labels only."},
}

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
    subject: Optional[str] = typer.Option(None, "--subject", "-s", help="Final subject/title (leave empty to infer)"),
    profile: str = typer.Option("", "--profile", help="Preset: clinical-masters|elections-focus|compressed-handbook|pop-explainer|bilingual-pairs"),
    length: str = typer.Option("long", "--length", help="Per-message length: standard|long|very-long|max"),
    span: str = typer.Option("book", "--span", help="Total span: medium|long|book"),
    out_path: str = typer.Option("", "--out", "-o", help="Output path (defaults to books/finals/<slug>.final.md)"),
    extra_file: List[str] = typer.Option([], "--extra-file", "-E", help="Append file(s) to system prompt (e.g., directives/_rules/rules.merged.md)"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Prompt to wait for browser capture before starting"),
):
    """
    1) Opens your editor to capture rough seeds.
    2) Asks AI to plan (YAML: subject, goal, focus, outline).
    3) Builds the final system prompt (narrative + no_bs by default or profile).
    4) (Optional) lets you append extra files (rules, domain sheets).
    5) Runs a long, dense book over the chosen span — no numbers.
    """
    cli: CLIContext = ctx.obj

    # Open editor for seeds
    seeds = typer.edit(_editor_seed())
    if not seeds or not seeds.strip():
        typer.echo("No seeds provided. Aborting.")
        raise typer.Exit(2)

    # Resolve descriptive presets
    L = LENGTH_PRESETS.get(length.lower())
    if not L:
        typer.echo("Unknown --length. Choose: standard|long|very-long|max")
        raise typer.Exit(2)
    total_chunks = SPAN_PRESETS.get(span.lower())
    if not total_chunks:
        typer.echo("Unknown --span. Choose: medium|long|book")
        raise typer.Exit(2)

    overlays = ["narrative", "no_bs"]  # default: narrative (not compressed)
    extra_note = ""
    if profile:
        spec = PROFILES.get(profile)
        if not spec:
            typer.echo(f"Unknown profile: {profile}")
            raise typer.Exit(2)
        overlays = spec["overlays"]
        extra_note = spec["extra"]

    # Ask AI to plan in YAML
    async def _plan():
        return await cli.engine.send_and_collect(_PLANNER_PROMPT.format(seeds=seeds), system_prompt=None)
    yaml_text = asyncio.run(_plan())

    # Parse YAML; fallbacks if needed
    plan = {}
    try:
        plan = yaml.safe_load(yaml_text) or {}
    except Exception:
        plan = {}
    plan_subject = (plan.get("subject") or subject or "Untitled Project").strip()

    # Compose system text using overlays + optional extra note
    comp = compose_prompt(
        subject=plan_subject,
        base="zero2hero",
        overlays=overlays,
        extra_notes=extra_note,
        min_chars=L["min"],
        passes=L["passes"],
        max_chunks=total_chunks,
    )
    system_text = comp.system_text

    # Inject outline-first scaffold if we got an outline
    if isinstance(plan.get("outline"), list) and plan["outline"]:
        # Format outline as a readable scaffold
        try:
            import textwrap
            outline_lines = []
            for idx, sec in enumerate(plan["outline"], 1):
                title = (sec.get("title") or f"Section {idx}").strip()
                cover = sec.get("cover") or []
                outline_lines.append(f"- {idx}. {title}")
                for b in cover:
                    outline_lines.append(f"    • {b}")
            scaffold = "\n".join(outline_lines)
            system_text += (
                "\n\nOUTLINE-FIRST SCAFFOLD\n"
                "- First chunk: produce a chapter-by-chapter outline consistent with this planner output; end with NEXT: [Begin Chapter 1].\n"
                "- Subsequent chunks: follow the outline; narrative prose; define terms once; no bullet walls.\n"
                "PLANNER OUTLINE (guidance):\n"
                + textwrap.dedent(scaffold)
            )
        except Exception:
            pass

    # Append extra files (rules, domain sheets)
    for ef in extra_file:
        ep = Path(ef)
        if ep.exists() and ep.is_file():
            try:
                system_text += "\n\n" + ep.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    # Output path
    if not out_path:
        out_path = f"./books/finals/{_slugify(plan_subject)}.final.md"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # Optional wait for capture
    if wait:
        typer.echo("\nOpen https://lmarena.ai and add '#bridge=8080' (or your port) to the URL.")
        typer.echo("Click 'Retry' on any message to activate the tab.")
        typer.echo("Press ENTER here to begin...")
        try:
            input()
        except KeyboardInterrupt:
            raise typer.Exit(1)

    # Build job and run
    rec = {
        "task": "book.zero2hero",
        "subject": plan_subject,
        "system_text": system_text,
        "max_chunks": total_chunks,
        "continuation": {"mode": "anchor", "minChars": L["min"], "pushPasses": L["passes"], "repeatWarn": True},
        "io": {"output": "file", "outPath": out_path},
    }
    runner = JobRunner({})
    job_id = runner.submit(playbook={"name": f"Plan run: {plan_subject}", **rec},
                           params={"max_chunks": rec["max_chunks"], "continuation": rec["continuation"], "io": rec["io"]})
    typer.echo(f"[plan] submitted: {job_id}")
    runner.run_job(job_id)
    typer.echo(f"[plan] done → {out_path}")