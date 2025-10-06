"""Lossless mode CLI commands for LMASudio."""

import typer

from ..core.backends import create_backend
from ..core.config import Config
from ..core.engine import Engine
from ..core.state import SessionState
from ..modes.lossless import LosslessMode

app = typer.Typer()


@app.command("ingest")
def lossless_ingest(
    text: str = typer.Argument(..., help="Text to ingest and synthesize")
):
    """Ingest and synthesize information from text."""
    config = Config()
    state = SessionState()
    backend = create_backend(
        config.backend,
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
    )
    engine = Engine(backend, state)
    lossless_mode = LosslessMode(engine)

    result = asyncio.run(lossless_mode.ingest_synth(text))
    print(result)


@app.command("rewrite")
def lossless_rewrite(
    text: str = typer.Argument(..., help="Text to rewrite while preserving meaning")
):
    """Rewrite text while preserving all meaning."""
    config = Config()
    state = SessionState()
    backend = create_backend(
        config.backend,
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
    )
    engine = Engine(backend, state)
    lossless_mode = LosslessMode(engine)

    result = asyncio.run(lossless_mode.rewrite_lossless(text))
    print(result)


@app.command("run")
def lossless_run(
    text: str = typer.Argument(
        ..., help="Text to process with comprehensive lossless processing"
    )
):
    """Perform a comprehensive lossless processing run."""
    config = Config()
    state = SessionState()
    backend = create_backend(
        config.backend,
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
    )
    engine = Engine(backend, state)
    lossless_mode = LosslessMode(engine)

    result = asyncio.run(lossless_mode.lossless_run(text))
    print(result)


@app.command("improve-flow")
def lossless_improve_flow(
    text: str = typer.Argument(..., help="Text to improve flow for")
):
    """Improve the flow and transitions in text."""
    config = Config()
    state = SessionState()
    backend = create_backend(
        config.backend,
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
    )
    engine = Engine(backend, state)
    lossless_mode = LosslessMode(engine)

    result = asyncio.run(lossless_mode.improve_flow(text))
    print(result)


@app.command("break-paragraphs")
def lossless_break_paragraphs(
    text: str = typer.Argument(..., help="Text to break into more readable paragraphs")
):
    """Break dense paragraphs into more readable chunks."""
    config = Config()
    state = SessionState()
    backend = create_backend(
        config.backend,
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
    )
    engine = Engine(backend, state)
    lossless_mode = LosslessMode(engine)

    result = asyncio.run(lossless_mode.break_paragraphs(text))
    print(result)


@app.command("enhance-structure")
def lossless_enhance_structure(
    text: str = typer.Argument(..., help="Text to enhance with better structure")
):
    """Enhance text structure with appropriate headings and formatting."""
    config = Config()
    state = SessionState()
    backend = create_backend(
        config.backend,
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
    )
    engine = Engine(backend, state)
    lossless_mode = LosslessMode(engine)

    result = asyncio.run(lossless_mode.enhance_structure(text))
    print(result)
