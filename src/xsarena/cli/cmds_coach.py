#!/usr/bin/env python3
import asyncio
import pathlib
import time

import typer

from ..core.backends import create_backend
from ..core.engine import Engine
from ..core.state import SessionState


# Define safe no-op fallbacks for optional modules
def _no_op_log_event(*args, **kwargs):
    """No-op fallback for log_event when joy module is not available."""
    return None


def _no_op_add_achievement(*args, **kwargs):
    """No-op fallback for add_achievement when joy module is not available."""
    return None


# Initialize with fallbacks
log_event = _no_op_log_event
add_achievement = _no_op_add_achievement


app = typer.Typer(help="Coach drills and Boss mini-exams")


def _ask_q(eng: Engine, subject: str):
    sys = "Generate a single short MCQ with 4 options (A-D) and the correct answer letter at the end on a new line like: ANSWER: C"
    rep = asyncio.run(eng.send_and_collect(f"Subject: {subject}", system_prompt=sys))
    return rep


@app.command("start")
def coach_start(subject: str, minutes: int = 10):
    # Import joy functions if available, otherwise use existing fallbacks
    global log_event, add_achievement
    try:
        from ..core.joy import add_achievement, log_event
    except ImportError:
        # Joy module is optional, keep using the fallbacks defined at module level
        pass

    try:
        eng = Engine(create_backend("openrouter"), SessionState())
    except ValueError:
        typer.echo(
            "Error: OpenRouter backend requires OPENROUTER_API_KEY environment variable to be set.",
            err=True,
        )
        raise typer.Exit(1)

    end = time.time() + minutes * 60
    score = 0
    asked = 0
    while time.time() < end:
        q = _ask_q(eng, subject)
        typer.echo("\n" + q)
        ans = input("Your answer (A-D, or q=quit): ").strip().upper()
        if ans == "Q":
            break
        correct = (
            "ANSWER:" in q
            and q.strip().splitlines()[-1].split(":")[-1].strip()[0].upper()
        )
        asked += 1
        if ans == correct:
            score += 1
            typer.echo("✅ Correct!\n")
        else:
            typer.echo(f"❌ Nope. Correct: {correct}\n")
    typer.echo(f"Coach done. Score: {score}/{asked}")
    log_event("coach", {"subject": subject, "score": score, "asked": asked})
    if asked >= 8 and score / asked >= 0.75:
        add_achievement("Coach Bronze")


@app.command("quiz")
def coach_quiz(subject: str, n: int = 10):
    """A quick N-question MCQ quiz."""
    # Import joy functions if available, otherwise use existing fallbacks
    global log_event, add_achievement
    try:
        from ..core.joy import add_achievement, log_event
    except ImportError:
        # Joy module is optional, keep using the fallbacks defined at module level
        pass

    try:
        eng = Engine(create_backend("openrouter"), SessionState())
    except ValueError:
        typer.echo(
            "Error: OpenRouter backend requires OPENROUTER_API_KEY environment variable to be set.",
            err=True,
        )
        raise typer.Exit(1)

    score = 0
    for _i in range(n):
        q = _ask_q(eng, subject)
        typer.echo("\n" + q)
        ans = input("Your answer (A-D): ").strip().upper()
        correct = (
            "ANSWER:" in q
            and q.strip().splitlines()[-1].split(":")[-1].strip()[0].upper()
        )
        if ans == correct:
            score += 1
            typer.echo("✅")
        else:
            typer.echo(f"❌ ({correct})")
    typer.echo(f"Quiz: {score}/{n}")
    log_event("quiz", {"subject": subject, "score": score, "n": n})


@app.command("boss")
def boss_start(subject: str, n: int = 20, minutes: int = 25):
    """Timed Boss mini-exam; auto-creates a repair prompt."""
    # Import joy functions if available, otherwise use existing fallbacks
    global log_event, add_achievement
    try:
        from ..core.joy import add_achievement, log_event
    except ImportError:
        # Joy module is optional, keep using the fallbacks defined at module level
        pass

    try:
        eng = Engine(create_backend("openrouter"), SessionState())
    except ValueError:
        typer.echo(
            "Error: OpenRouter backend requires OPENROUTER_API_KEY environment variable to be set.",
            err=True,
        )
        raise typer.Exit(1)

    end = time.time() + minutes * 60
    score = 0
    asked = 0
    misses = []
    while time.time() < end and asked < n:
        q = _ask_q(eng, subject)
        typer.echo("\n" + q)
        ans = input("Your answer (A-D, or q=quit): ").strip().upper()
        if ans == "Q":
            break
        correct = (
            "ANSWER:" in q
            and q.strip().splitlines()[-1].split(":")[-1].strip()[0].upper()
        )
        asked += 1
        if ans == correct:
            score += 1
            typer.echo("✅")
        else:
            misses.append({"q": q, "your": ans, "correct": correct})
            typer.echo(f"❌ ({correct})")
    typer.echo(f"Boss fought: {score}/{asked}")
    log_event("boss", {"subject": subject, "score": score, "asked": asked})
    # Auto repair chapter prompt
    if misses:
        sys = "Write a short repair chapter focused on the following misses. Teach-before-use; add 3 quick checks; 3 pitfalls; end with NEXT: [Continue]."
        pack = "\n\n".join(
            m["q"] + f"\nYOUR:{m['your']}\nCORRECT:{m['correct']}" for m in misses[:8]
        )
        rep = asyncio.run(
            eng.send_and_collect(
                f"Subject: {subject}\nMISSES:\n{pack}", system_prompt=sys
            )
        )
        out = pathlib.Path("books") / f"{subject.lower().replace(' ','-')}.repair.md"
        out.write_text(rep, encoding="utf-8")
        typer.echo(f"Repair chapter → {out}")
        if score / asked >= 0.8:
            add_achievement("Boss Bronze")
