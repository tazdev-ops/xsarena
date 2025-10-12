#!/usr/bin/env python3
import json
import pathlib
from typing import Optional

import typer

from ..core.backends import create_backend
from ..core.engine import Engine
from ..core.roleplay import (
    append_turn,
    export_markdown,
    load_session,
    new_session,
    redact_boundary_violations,
    save_session,
)
from ..core.state import SessionState

app = typer.Typer(help="Roleplay engine: start, say, boundaries, model, export")


def _load_personas():
    import yaml

    p = pathlib.Path("directives") / "roleplay" / "personas.yml"
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")).get("personas", {})


@app.command("list")
def rp_list_personas():
    personas = _load_personas()
    for key, val in personas.items():
        print(f"{key}: {val.get('title','')}")


@app.command("start")
def rp_start(
    name: str = typer.Argument(..., help="Session name"),
    persona: str = typer.Option("socratic_tutor", "--persona"),
    backend: str = typer.Option("openrouter", "--backend"),
    model: Optional[str] = typer.Option(None, "--model"),
    rating: str = typer.Option("sfw", "--rating"),
    safeword: str = typer.Option("PAUSE", "--safeword"),
):
    personas = _load_personas()
    if persona not in personas:
        print("Unknown persona. Use: xsarena rp list")
        raise typer.Exit(1)
    overlay = personas[persona].get("overlay", "")
    s = new_session(
        name=name,
        persona=persona,
        overlay=overlay,
        backend=backend,
        model=model,
        rating=rating,
        safeword=safeword,
    )
    print(
        json.dumps(
            {
                "rp_id": s.id,
                "name": s.name,
                "persona": persona,
                "backend": backend,
                "model": model or "(default)",
            }
        )
    )


@app.command("say")
def rp_say(sess_id: str, text: str):
    s = load_session(sess_id)
    # Safeword check
    if s.boundaries.safeword and s.boundaries.safeword in text:
        append_turn(
            sess_id,
            "assistant",
            "Safeword received. Pausing. Do you want a summary or to resume?",
        )
        print("PAUSED.")
        return
    # Append user turn
    append_turn(sess_id, "user", text)
    # Build engine and system prompt
    eng = Engine(create_backend(s.backend, model=s.model), SessionState())
    sys = f"{s.system_overlay}\n\nBoundaries: {s.boundaries.rating.upper()}; no illegal content; English only; if unsafe prompt, refuse briefly."
    # Use a tiny context: last few turns + memory
    ctx = load_session(sess_id)  # reload to get latest
    turns = ctx.turns[-6:]  # small history
    # Compose user prompt (include memory for continuity)
    mem = ""
    if ctx.memory:
        mem = "MEMORY:\n- " + "\n- ".join(ctx.memory) + "\n\n"
    user = (
        mem
        + "\n".join(
            f"{t['role']}: {t['content']}"
            for t in turns
            if t["role"] in ("user", "assistant")
        )
        + "\nassistant:"
    )
    reply = eng.send_and_collect(user, system_prompt=sys)
    reply = redact_boundary_violations(s.boundaries, reply)
    append_turn(sess_id, "assistant", reply)
    print(reply)
    # Check if we should award an achievement
    current_session = load_session(sess_id)
    if len(current_session.turns) >= 10:
        from ..core.joy import add_achievement

        add_achievement("RP Explorer")


@app.command("mem")
def rp_memory(
    sess_id: str,
    add: Optional[str] = typer.Option(None, "--add"),
    show: bool = typer.Option(False, "--show"),
):
    s = load_session(sess_id)
    if add:
        s.memory.append(add)
        save_session(s)
        print("Added to memory.")
    if show or not add:
        for i, m in enumerate(s.memory, start=1):
            print(f"{i}. {m}")


@app.command("model")
def rp_model(
    sess_id: str,
    backend: Optional[str] = typer.Option(None, "--backend"),
    model: Optional[str] = typer.Option(None, "--model"),
):
    s = load_session(sess_id)
    if backend:
        s.backend = backend
    if model:
        s.model = model
    save_session(s)
    print(json.dumps({"backend": s.backend, "model": s.model or "(default)"}))


@app.command("bounds")
def rp_bounds(
    sess_id: str,
    rating: Optional[str] = typer.Option(None, "--rating"),
    safeword: Optional[str] = typer.Option(None, "--safeword"),
):
    s = load_session(sess_id)
    if rating:
        s.boundaries.rating = rating
    if safeword:
        s.boundaries.safeword = safeword
    save_session(s)
    print(
        json.dumps({"rating": s.boundaries.rating, "safeword": s.boundaries.safeword})
    )


@app.command("export")
def rp_export(sess_id: str):
    p = export_markdown(sess_id)
    if p:
        print(f"Transcript → {p}")
    else:
        print("No transcript found.")


#!/usr/bin/env python3
import time

import typer

from ..core.joy import add_achievement, log_event

app = typer.Typer(help="Coach drills and Boss mini-exams")


def _ask_q(eng: Engine, subject: str):
    sys = "Generate a single short MCQ with 4 options (A-D) and the correct answer letter at the end on a new line like: ANSWER: C"
    rep = eng.send_and_collect(f"Subject: {subject}", system_prompt=sys)
    return rep


@app.command("start")
def coach_start(subject: str, minutes: int = 10):
    """Timed coach drill with immediate feedback."""
    eng = Engine(create_backend("openrouter"), SessionState())
    end = time.time() + minutes * 60
    score = 0
    asked = 0
    while time.time() < end:
        q = _ask_q(eng, subject)
        print("\n" + q)
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
            print("✅ Correct!\n")
        else:
            print(f"❌ Nope. Correct: {correct}\n")
    print(f"Coach done. Score: {score}/{asked}")
    log_event("coach", {"subject": subject, "score": score, "asked": asked})
    if asked >= 8 and score / asked >= 0.75:
        add_achievement("Coach Bronze")


@app.command("quiz")
def coach_quiz(subject: str, n: int = 10):
    """A quick N-question MCQ quiz."""
    eng = Engine(create_backend("openrouter"), SessionState())
    score = 0
    for i in range(n):
        q = _ask_q(eng, subject)
        print("\n" + q)
        ans = input("Your answer (A-D): ").strip().upper()
        correct = (
            "ANSWER:" in q
            and q.strip().splitlines()[-1].split(":")[-1].strip()[0].upper()
        )
        if ans == correct:
            score += 1
            print("✅")
        else:
            print(f"❌ ({correct})")
    print(f"Quiz: {score}/{n}")
    log_event("quiz", {"subject": subject, "score": score, "n": n})


@app.command("boss")
def boss_start(subject: str, n: int = 20, minutes: int = 25):
    """Timed Boss mini-exam; auto-creates a repair prompt."""
    eng = Engine(create_backend("openrouter"), SessionState())
    end = time.time() + minutes * 60
    score = 0
    asked = 0
    misses = []
    while time.time() < end and asked < n:
        q = _ask_q(eng, subject)
        print("\n" + q)
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
            print("✅")
        else:
            misses.append({"q": q, "your": ans, "correct": correct})
            print(f"❌ ({correct})")
    print(f"Boss fought: {score}/{asked}")
    log_event("boss", {"subject": subject, "score": score, "asked": asked})
    # Auto repair chapter prompt
    if misses:
        sys = "Write a short repair chapter focused on the following misses. Teach-before-use; add 3 quick checks; 3 pitfalls; end with NEXT: [Continue]."
        pack = "\n\n".join(
            m["q"] + f"\nYOUR:{m['your']}\nCORRECT:{m['correct']}" for m in misses[:8]
        )
        rep = eng.send_and_collect(
            f"Subject: {subject}\nMISSES:\n{pack}", system_prompt=sys
        )
        out = pathlib.Path("books") / f"{subject.lower().replace(' ','-')}.repair.md"
        out.write_text(rep, encoding="utf-8")
        print(f"Repair chapter → {out}")
        if score / asked >= 0.8:
            add_achievement("Boss Bronze")
