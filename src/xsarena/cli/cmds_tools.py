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
