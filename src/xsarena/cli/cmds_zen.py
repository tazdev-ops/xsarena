#!/usr/bin/env python3
import time

import typer

from ..core.backends import create_backend
from ..core.engine import Engine
from ..core.state import SessionState

app = typer.Typer(help="Zen focus sessions")

ZEN = {"on": False}


@app.command("on")
def zen_on():
    ZEN["on"] = True
    print("[zen] ON — minimal logs, smooth pacing.")


@app.command("off")
def zen_off():
    ZEN["on"] = False
    print("[zen] OFF")


@app.command("session")
def zen_session(subject: str, minutes: int = 25):
    eng = Engine(create_backend("openrouter"), SessionState())
    sys = "Teach-before-use; smooth narrative; ~3000 chars; end with NEXT: [Continue]. No meta."
    end = time.time() + minutes * 60
    i = 0
    while time.time() < end:
        i += 1
        reply = eng.send_and_collect(f"Subject: {subject}\nChunk {i}", system_prompt=sys)
        print(reply[:300] + "\n...\n")  # show snippet only
        left = max(0, int(end - time.time()))
        print(f"[zen] Time left ~{left//60}m {left%60}s")
        break  # single chunk for now (extend if you wish)
