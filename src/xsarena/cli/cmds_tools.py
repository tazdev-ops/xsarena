#!/usr/bin/env python3
import asyncio
import typer

from ..core.backends import create_backend
from ..core.engine import Engine
from ..core.state import SessionState

app = typer.Typer(help="Fun explainers, personas, and toggles")


@app.command("eli5")
def fun_eli5(topic: str):
    eng = Engine(create_backend("openrouter"), SessionState())
    sys = "Explain like I'm five (ELI5): plain, short sentences; vivid but accurate analogies; 120–180 words."
    print(asyncio.run(eng.send_and_collect(topic, system_prompt=sys)))


@app.command("story")
def fun_story(concept: str):
    eng = Engine(create_backend("openrouter"), SessionState())
    sys = "Explain the concept with a short story that aids memory. 200–300 words; accurate; one clear moral at end."
    print(asyncio.run(eng.send_and_collect(concept, system_prompt=sys)))


@app.command("persona")
def fun_persona(name: str):
    """chad|prof|coach — set persona overlay (session, not global)"""
    overlays = {
        "chad": "Persona: Chad — decisive, evidence-first, no fluff; end with Bottom line.",
        "prof": "Persona: Professor — structured, cites sources sparingly, neutral tone.",
        "coach": "Persona: Coach — encouraging, actionable next steps, no fluff.",
    }
    print(overlays.get(name.lower(), "Unknown persona. Try chad|prof|coach."))


@app.command("nobs")
def fun_nobs(flag: str):
    """on|off — alias to no‑BS"""
    if flag.lower() not in ("on", "off"):
        print("Use: xsarena fun nobs on|off")
        return
    print(f"(alias) Run: /style.nobs {flag.lower()}")


#!/usr/bin/env python3
import random

import typer

app = typer.Typer(help="Daily joy, streaks, achievements, and surprises")


@app.command("daily")
def joy_daily(subject: str):
    """10-minute micro-plan for the day: 1 subtopic, 2 quick checks, 1 pitfall, 1 flashcard seed."""
    try:
        from ..core.joy import add_achievement, bump_streak, get_state, log_event, sparkline
    except ImportError:
        typer.echo("Error: core.joy module not available. This is an optional extra.", err=True)
        typer.echo("To enable this feature, install the extras: pip install xsarena[extras]", err=True)
        raise typer.Exit(1)
        
    eng = Engine(create_backend("openrouter"), SessionState())
    sys = (
        "You are a friendly study coach. Create a 10-minute micro-plan for the given subject:\n"
        "- 1 subtopic\n- 2 quick checks\n- 1 pitfall to avoid\n- 1 flashcard seed (Q/A)\nKeep it compact."
    )
    reply = asyncio.run(eng.send_and_collect(f"Subject: {subject}", system_prompt=sys))
    streak = bump_streak()
    add_achievement("First Daily") if streak == 1 else None
    log_event("daily", {"subject": subject})
    print(f"Streak: {streak}  [{sparkline(7)}]\n")
    print(reply)


@app.command("streak")
def joy_streak():
    try:
        from ..core.joy import get_state, sparkline
    except ImportError:
        typer.echo("Error: core.joy module not available. This is an optional extra.", err=True)
        typer.echo("To enable this feature, install the extras: pip install xsarena[extras]", err=True)
        raise typer.Exit(1)
        
    s = get_state()
    print(f"Streak: {s['streak']}  [{sparkline(7)}]  Last: {s.get('last_day')}")
    if s["achievements"]:
        print("Achievements:", ", ".join(s["achievements"]))


@app.command("achievements")
def joy_achievements():
    try:
        from ..core.joy import get_state
    except ImportError:
        typer.echo("Error: core.joy module not available. This is an optional extra.", err=True)
        typer.echo("To enable this feature, install the extras: pip install xsarena[extras]", err=True)
        raise typer.Exit(1)
        
    s = get_state()
    print("Achievements:", ", ".join(s["achievements"]) or "(none)")


@app.command("kudos")
def joy_kudos():
    try:
        from ..core.joy import get_state, sparkline
    except ImportError:
        # If joy module is not available, just show a simple message
        pass
        
    msgs = [
        "You're on fire! 🔥",
        "Another brick in the wall. 🧱",
        "Small steps make mountains. ⛰️",
        "Great focus—keep shipping. 🚀",
    ]
    print(random.choice(msgs))
