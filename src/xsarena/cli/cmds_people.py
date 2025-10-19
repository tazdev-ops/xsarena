#!/usr/bin/env python3
import asyncio
import json
import pathlib
from typing import Optional

import typer

from ..core.backends import create_backend
from ..core.engine import Engine
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
    try:
        from ..core.roleplay import load_session, new_session, save_session
    except ImportError:
        typer.echo(
            "Feature not included in this build. See documentation for installation instructions.",
            err=True,
        )
        raise typer.Exit(1)

    personas = _load_personas()
    for key, val in personas.items():
        typer.echo(f"{key}: {val.get('title','')}")


@app.command("start")
def rp_start(
    name: str = typer.Argument(..., help="Session name"),
    persona: str = typer.Option("socratic_tutor", "--persona"),
    backend: str = typer.Option("openrouter", "--backend"),
    model: Optional[str] = typer.Option(None, "--model"),
    rating: str = typer.Option("sfw", "--rating"),
    safeword: str = typer.Option("PAUSE", "--safeword"),
):
    try:
        from ..core.roleplay import (
            append_turn,
            export_markdown,
            load_session,
            new_session,
            redact_boundary_violations,
            save_session,
        )
    except ImportError:
        typer.echo(
            "Feature not included in this build. See documentation for installation instructions.",
            err=True,
        )
        raise typer.Exit(1)

    personas = _load_personas()
    if persona not in personas:
        typer.echo("Unknown persona. Use: xsarena rp list")
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
    typer.echo(
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
    try:
        from ..core.roleplay import (
            append_turn,
            export_markdown,
            load_session,
            new_session,
            redact_boundary_violations,
            save_session,
        )
    except ImportError:
        typer.echo(
            "Feature not included in this build. See documentation for installation instructions.",
            err=True,
        )
        raise typer.Exit(1)

    s = load_session(sess_id)
    # Safeword check
    if s.boundaries.safeword and s.boundaries.safeword in text:
        append_turn(
            sess_id,
            "assistant",
            "Safeword received. Pausing. Do you want a summary or to resume?",
        )
        typer.echo("PAUSED.")
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
    reply = asyncio.run(eng.send_and_collect(user, system_prompt=sys))
    reply = redact_boundary_violations(s.boundaries, reply)
    append_turn(sess_id, "assistant", reply)
    typer.echo(reply)
    # Check if we should award an achievement
    current_session = load_session(sess_id)
    if len(current_session.turns) >= 10:
        try:
            from ..core.joy import add_achievement

            add_achievement("RP Explorer")
        except ImportError:
            # Joy module is optional, skip achievement
            pass


@app.command("mem")
def rp_memory(
    sess_id: str,
    add: Optional[str] = typer.Option(None, "--add"),
    show: bool = typer.Option(False, "--show"),
):
    try:
        from ..core.roleplay import (
            append_turn,
            export_markdown,
            load_session,
            new_session,
            redact_boundary_violations,
            save_session,
        )
    except ImportError:
        typer.echo(
            "Feature not included in this build. See documentation for installation instructions.",
            err=True,
        )
        raise typer.Exit(1)

    s = load_session(sess_id)
    if add:
        s.memory.append(add)
        save_session(s)
        typer.echo("Added to memory.")
    if show or not add:
        for i, m in enumerate(s.memory, start=1):
            typer.echo(f"{i}. {m}")


@app.command("model")
def rp_model(
    sess_id: str,
    backend: Optional[str] = typer.Option(None, "--backend"),
    model: Optional[str] = typer.Option(None, "--model"),
):
    try:
        from ..core.roleplay import (
            append_turn,
            export_markdown,
            load_session,
            new_session,
            redact_boundary_violations,
            save_session,
        )
    except ImportError:
        typer.echo(
            "Feature not included in this build. See documentation for installation instructions.",
            err=True,
        )
        raise typer.Exit(1)

    s = load_session(sess_id)
    if backend:
        s.backend = backend
    if model:
        s.model = model
    save_session(s)
    typer.echo(json.dumps({"backend": s.backend, "model": s.model or "(default)"}))


@app.command("bounds")
def rp_bounds(
    sess_id: str,
    rating: Optional[str] = typer.Option(None, "--rating"),
    safeword: Optional[str] = typer.Option(None, "--safeword"),
):
    try:
        from ..core.roleplay import (
            append_turn,
            export_markdown,
            load_session,
            new_session,
            redact_boundary_violations,
            save_session,
        )
    except ImportError:
        typer.echo(
            "Feature not included in this build. See documentation for installation instructions.",
            err=True,
        )
        raise typer.Exit(1)

    s = load_session(sess_id)
    if rating:
        s.boundaries.rating = rating
    if safeword:
        s.boundaries.safeword = safeword
    save_session(s)
    typer.echo(
        json.dumps({"rating": s.boundaries.rating, "safeword": s.boundaries.safeword})
    )


@app.command("export")
def rp_export(sess_id: str):
    try:
        from ..core.roleplay import (
            append_turn,
            export_markdown,
            load_session,
            new_session,
            redact_boundary_violations,
            save_session,
        )
    except ImportError:
        typer.echo(
            "Feature not included in this build. See documentation for installation instructions.",
            err=True,
        )
        raise typer.Exit(1)

    p = export_markdown(sess_id)
    if p:
        typer.echo(f"Transcript → {p}")
    else:
        typer.echo("No transcript found.")
