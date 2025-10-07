#!/usr/bin/env python3
import pathlib

import typer

from ..core.backends import create_backend
from ..core.engine import Engine
from ..core.state import SessionState

app = typer.Typer(help="Capture and apply styles")


@app.command("capture")
def style_capture(input_file: str, out_file: str):
    text = pathlib.Path(input_file).read_text(encoding="utf-8")
    sys_prompt = (
        "You are a style profiler. Extract voice: tone, rhythm, sentence length, vocabulary, structure, devices, openings/closings, formatting, no-goes.\n"
        "Return a STYLE PROFILE (Markdown), no meta."
    )
    eng = Engine(create_backend("openrouter"), SessionState())  # use current backend if you prefer
    reply = eng.send_and_collect(text, system_prompt=sys_prompt)
    pathlib.Path(out_file).write_text(reply, encoding="utf-8")
    typer.echo(f"[style] Saved profile → {out_file}")


@app.command("apply")
def style_apply(style_file: str, input_file: str, out_file: str):
    style = pathlib.Path(style_file).read_text(encoding="utf-8")
    content = pathlib.Path(input_file).read_text(encoding="utf-8")
    sys_prompt = (
        "You are applying a captured style to new content.\nSTYLE:\n<<<\n" + style + "\n>>>\n"
        "Rewrite content in this style. Preserve meaning; no loss of facts."
    )
    eng = Engine(create_backend("openrouter"), SessionState())
    reply = eng.send_and_collect(content, system_prompt=sys_prompt)
    pathlib.Path(out_file).write_text(reply, encoding="utf-8")
    typer.echo(f"[style] Wrote → {out_file}")
