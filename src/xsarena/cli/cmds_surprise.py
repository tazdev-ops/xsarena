#!/usr/bin/env python3
import random

import typer

from ..core.backends import create_backend
from ..core.engine import Engine
from ..core.state import SessionState

app = typer.Typer(help="Surprise me!")


@app.command("run")
def surprise_run(subject: str):
    eng = Engine(create_backend("openrouter"), SessionState())
    options = [
        ("Mini-cram", "Create a one-page high-yield cram sheet: definitions, pitfalls, quick checks."),
        ("Metaphor", "Explain with a powerful metaphor and one counterexample."),
        ("Vignette", "Teach via a short real-world vignette; end with 3 questions to the reader."),
        ("Quick drill", "Make 5 rapid-fire Q&A (1 line each)."),
    ]
    title, prompt = random.choice(options)
    print(f"🎲 {title}\n")
    print(
        eng.send_and_collect(
            f"Subject: {subject}\nTask: {prompt}", system_prompt="English only. Precision over flourish."
        )
    )
