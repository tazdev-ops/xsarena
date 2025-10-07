#!/usr/bin/env python3
import random

import typer

from ..core.backends import create_backend
from ..core.engine import Engine
from ..core.joy import add_achievement, bump_streak, get_state, log_event, sparkline
from ..core.state import SessionState

app = typer.Typer(help="Daily joy, streaks, achievements, and surprises")


@app.command("daily")
def joy_daily(subject: str):
    """10-minute micro-plan for the day: 1 subtopic, 2 quick checks, 1 pitfall, 1 flashcard seed."""
    eng = Engine(create_backend("openrouter"), SessionState())
    sys = (
        "You are a friendly study coach. Create a 10-minute micro-plan for the given subject:\n"
        "- 1 subtopic\n- 2 quick checks\n- 1 pitfall to avoid\n- 1 flashcard seed (Q/A)\nKeep it compact."
    )
    reply = eng.send_and_collect(f"Subject: {subject}", system_prompt=sys)
    streak = bump_streak()
    add_achievement("First Daily") if streak == 1 else None
    log_event("daily", {"subject": subject})
    print(f"Streak: {streak}  [{sparkline(7)}]\n")
    print(reply)


@app.command("streak")
def joy_streak():
    s = get_state()
    print(f"Streak: {s['streak']}  [{sparkline(7)}]  Last: {s.get('last_day')}")
    if s["achievements"]:
        print("Achievements:", ", ".join(s["achievements"]))


@app.command("achievements")
def joy_achievements():
    s = get_state()
    print("Achievements:", ", ".join(s["achievements"]) or "(none)")


@app.command("kudos")
def joy_kudos():
    msgs = [
        "You're on fire! 🔥",
        "Another brick in the wall. 🧱",
        "Small steps make mountains. ⛰️",
        "Great focus—keep shipping. 🚀",
    ]
    print(random.choice(msgs))
