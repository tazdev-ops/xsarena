"""Consolidated authoring commands for XSArena."""

import asyncio
from pathlib import Path

import typer

from ..modes.lossless import LosslessMode
from .context import CLIContext

app = typer.Typer(help="Content creation, ingestion, and style tools.")

# --- Ingest Commands ---

INGEST_SYSTEM_SYNTH = (
    """You are a synthesis engine. You will receive the previous Synthesis and a new CHUNK.\n"""
    """Update the Synthesis to incorporate the new material. Keep it compact but complete:\n"""
    """structured outline of topics, key claims, procedures, defaults, signature heuristics, and stylistic guidance.\n"""
    """Preserve earlier coverage; merge or refactor as needed.\n"""
    """Return ONLY the updated Synthesis (Markdown), no commentary, no code fences."""
)

INGEST_SYSTEM_STYLE = (
    """You are a style analysis engine. You will receive the previous Style Profile and a new CHUNK.\n"""
    """Update the Style Profile to incorporate the new material's writing style, tone, and structure.\n"""
    """Focus on: prose patterns, sentence structure, vocabulary choices, narrative flow, and distinctive stylistic elements.\n"""
    """Preserve earlier coverage; merge or refactor as needed.\n"""
    """Return ONLY the updated Style Profile (Markdown), no commentary, no code fences."""
)

INGEST_SYSTEM_ACK = (
    """You are an acknowledgment engine. You will receive a CHUNK of text.\n"""
    """Acknowledge receipt of this content by briefly summarizing its main points in 1-2 sentences.\n"""
    """Return ONLY the acknowledgment summary (plain text), no commentary."""
)


def chunks_by_bytes(text: str, max_bytes: int):
    b = text.encode("utf-8")
    out = []
    i = 0
    n = len(b)
    while i < n:
        j = min(i + max_bytes, n)
        if j < n:
            k = b.rfind(b"\\n", i, j)
            if k != -1 and (j - k) < 2048:
                j = k
        part = b[i:j]
        while True:
            try:
                s = part.decode("utf-8")
                break
            except UnicodeDecodeError:
                part = part[:-1]
        out.append(s)
        i = j
    return out


def ingest_user_synth(i, n, synth_text, chunk, limit_chars):
    synth_excerpt = (
        synth_text[-limit_chars:] if len(synth_text) > limit_chars else synth_text
    )
    return (
        f"INGEST CHUNK {i}/{n}\\n\\n"
        f"PREVIOUS SYNTHESIS (<= {limit_chars} chars):\\n<<<SYNTHESIS\\n{synth_excerpt}\\nSYNTHESIS>>>\\n\\n"
        f"NEW CHUNK:\\n<<<CHUNK\\n{chunk}\\nCHUNK>>>\\n\\n"
        f"TASK:\\n"
        f"- Update the Synthesis above to fully include the NEW CHUNK's information.\\n"
        f"- Keep the updated Synthesis within ~{limit_chars} characters (short, dense).\\n"
        f"- Return ONLY the updated Synthesis (Markdown), no commentary.\\n"
    )


def ingest_user_style(i, n, style_text, chunk, limit_chars):
    style_excerpt = (
        style_text[-limit_chars:] if len(style_text) > limit_chars else style_text
    )
    return (
        f"INGEST CHUNK {i}/{n}\\n\\n"
        f"PREVIOUS STYLE PROFILE (<= {limit_chars} chars):\\n<<<STYLE\\n{style_excerpt}\\nSTYLE>>>\\n\\n"
        f"NEW CHUNK:\\n<<<CHUNK\\n{chunk}\\nCHUNK>>>\\n\\n"
        f"TASK:\\n"
        f"- Update the Style Profile above to incorporate the NEW CHUNK's writing style.\\n"
        f"- Focus on prose patterns, sentence structure, vocabulary, and narrative flow.\\n"
        f"- Keep the updated Style Profile within ~{limit_chars} characters (short, dense).\\n"
        f"- Return ONLY the updated Style Profile (Markdown), no commentary.\\n"
    )


def ingest_user_ack(i, n, chunk):
    return (
        f"INGEST CHUNK {i}/{n}\\n\\n"
        f"CHUNK:\\n<<<CHUNK\\n{chunk}\\nCHUNK>>>\\n\\n"
        f"TASK:\\n"
        f"- Acknowledge receipt of this content by briefly summarizing its main points in 1-2 sentences.\\n"
        f"- Return ONLY the acknowledgment summary (plain text), no commentary.\\n"
    )


@app.command("ingest-ack")
def ingest_ack(
    ctx: typer.Context,
    source_file: str = typer.Argument(..., help="Path to the source file to ingest."),
    chunk_kb: int = typer.Option(
        45, "--chunk-kb", help="Size of each chunk in kilobytes."
    ),
):
    """Ingest a large document in 'acknowledge' mode with 'OK i/N' handshake loop."""
    cli: CLIContext = ctx.obj
    source_path = Path(source_file)

    if not source_path.exists():
        typer.echo(f"Error: Source file not found at {source_path}", err=True)
        raise typer.Exit(1)

    text = source_path.read_text(encoding="utf-8")
    chunk_bytes = max(10_000, int(chunk_kb * 1024))
    parts = chunks_by_bytes(text, chunk_bytes)

    typer.echo(f"Ingest ACK mode: {len(parts)} chunks (~{chunk_kb} KB each)")

    async def _run_loop():
        for idx, chunk in enumerate(parts, start=1):
            user_prompt = ingest_user_ack(idx, len(parts), chunk)
            reply = await cli.engine.send_and_collect(
                user_prompt, system_prompt=INGEST_SYSTEM_ACK
            )
            ack_text = reply.strip()
            typer.echo(f"OK {idx}/{len(parts)} - {ack_text}")

    asyncio.run(_run_loop())
    typer.echo(f"Acknowledgment complete. Processed {len(parts)} chunks.")


@app.command("ingest-synth")
def ingest_synth(
    ctx: typer.Context,
    source_file: str = typer.Argument(..., help="Path to the source file to ingest."),
    output_file: str = typer.Argument(
        ..., help="Path to write the final synthesis to."
    ),
    chunk_kb: int = typer.Option(
        45, "--chunk-kb", help="Size of each chunk in kilobytes."
    ),
    synth_chars: int = typer.Option(
        9500, "--synth-chars", help="Character limit for the rolling synthesis prompt."
    ),
):
    """Ingest a large document in 'synthesis' mode with rolling update loop."""
    cli: CLIContext = ctx.obj
    source_path = Path(source_file)
    output_path = Path(output_file)

    if not source_path.exists():
        typer.echo(f"Error: Source file not found at {source_path}", err=True)
        raise typer.Exit(1)

    text = source_path.read_text(encoding="utf-8")
    chunk_bytes = max(10_000, int(chunk_kb * 1024))
    parts = chunks_by_bytes(text, chunk_bytes)
    synth_text = ""

    typer.echo(
        f"Ingest SYNTH mode: {len(parts)} chunks (~{chunk_kb} KB each); synth limit ~{synth_chars} chars"
    )

    async def _run_loop():
        nonlocal synth_text
        for idx, chunk in enumerate(parts, start=1):
            user_prompt = ingest_user_synth(
                idx, len(parts), synth_text, chunk, synth_chars
            )
            reply = await cli.engine.send_and_collect(
                user_prompt, system_prompt=INGEST_SYSTEM_SYNTH
            )
            synth_text = reply.strip()
            output_path.write_text(synth_text, encoding="utf-8")
            typer.echo(
                f"Synth updated {idx}/{len(parts)} — {len(synth_text)} chars written to {output_path}"
            )

    asyncio.run(_run_loop())
    typer.echo(f"Synthesis complete. Final output saved to: {output_path}")


@app.command("ingest-style")
def ingest_style(
    ctx: typer.Context,
    source_file: str = typer.Argument(..., help="Path to the source file to ingest."),
    output_file: str = typer.Argument(
        ..., help="Path to write the final style profile to."
    ),
    chunk_kb: int = typer.Option(
        45, "--chunk-kb", help="Size of each chunk in kilobytes."
    ),
    style_chars: int = typer.Option(
        6000,
        "--style-chars",
        help="Character limit for the rolling style profile prompt.",
    ),
):
    """Ingest a large document in 'style' mode with rolling style profile update loop."""
    cli: CLIContext = ctx.obj
    source_path = Path(source_file)
    output_path = Path(output_file)

    if not source_path.exists():
        typer.echo(f"Error: Source file not found at {source_path}", err=True)
        raise typer.Exit(1)

    text = source_path.read_text(encoding="utf-8")
    chunk_bytes = max(10_000, int(chunk_kb * 1024))
    parts = chunks_by_bytes(text, chunk_bytes)
    style_text = ""

    typer.echo(
        f"Ingest STYLE mode: {len(parts)} chunks (~{chunk_kb} KB each); style limit ~{style_chars} chars"
    )

    async def _run_loop():
        nonlocal style_text
        for idx, chunk in enumerate(parts, start=1):
            user_prompt = ingest_user_style(
                idx, len(parts), style_text, chunk, style_chars
            )
            reply = await cli.engine.send_and_collect(
                user_prompt, system_prompt=INGEST_SYSTEM_STYLE
            )
            style_text = reply.strip()
            output_path.write_text(style_text, encoding="utf-8")
            typer.echo(
                f"Style profile updated {idx}/{len(parts)} — {len(style_text)} chars written to {output_path}"
            )

    asyncio.run(_run_loop())
    typer.echo(f"Style profiling complete. Final output saved to: {output_path}")


@app.command("ingest-run")
def ingest_run(
    ctx: typer.Context,
    source_file: str = typer.Argument(..., help="Path to the source file to ingest."),
    output_file: str = typer.Argument(
        ..., help="Path to write the final synthesis to."
    ),
    chunk_kb: int = typer.Option(
        45, "--chunk-kb", help="Size of each chunk in kilobytes."
    ),
    synth_chars: int = typer.Option(
        9500, "--synth-chars", help="Character limit for the rolling synthesis prompt."
    ),
):
    """Ingest a large document and create a dense synthesis (alias for synth mode)."""
    ingest_synth(ctx, source_file, output_file, chunk_kb, synth_chars)


# --- Lossless Commands ---

@app.command("lossless-ingest")
def lossless_ingest(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to ingest and synthesize"),
):
    """Ingest and synthesize information from text."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.ingest_synth(text))
    typer.echo(result)


@app.command("lossless-rewrite")
def lossless_rewrite(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to rewrite while preserving meaning"),
):
    """Rewrite text while preserving all meaning."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.rewrite_lossless(text))
    typer.echo(result)


@app.command("lossless-run")
def lossless_run(
    ctx: typer.Context,
    text: str = typer.Argument(
        ..., help="Text to process with comprehensive lossless processing"
    ),
):
    """Perform a comprehensive lossless processing run."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.lossless_run(text))
    typer.echo(result)


@app.command("lossless-improve-flow")
def lossless_improve_flow(
    ctx: typer.Context, text: str = typer.Argument(..., help="Text to improve flow for")
):
    """Improve the flow and transitions in text."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.improve_flow(text))
    typer.echo(result)


@app.command("lossless-break-paragraphs")
def lossless_break_paragraphs(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to break into more readable paragraphs"),
):
    """Break dense paragraphs into more readable chunks."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.break_paragraphs(text))
    typer.echo(result)


@app.command("lossless-enhance-structure")
def lossless_enhance_structure(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to enhance with better structure"),
):
    """Enhance text structure with appropriate headings and formatting."""
    cli: CLIContext = ctx.obj
    lossless_mode = LosslessMode(cli.engine)

    result = asyncio.run(lossless_mode.enhance_structure(text))
    typer.echo(result)


# --- Style Commands ---

@app.command("style-narrative")
def style_narrative(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Enable or disable the narrative/pedagogy overlay for the session."""
    cli: CLIContext = ctx.obj
    if enable:
        cli.state.overlays_active.add("narrative")
    else:
        cli.state.overlays_active.discard("narrative")
    cli.save()
    status = "ON" if enable else "OFF"
    typer.echo(f"Narrative overlay set to: {status}")


@app.command("style-nobs")
def style_nobs(ctx: typer.Context, enable: bool = typer.Argument(True)):
    """Enable or disable the no-bullshit (no-bs) language overlay."""
    cli: CLIContext = ctx.obj
    if enable:
        cli.state.overlays_active.add("no_bs")
    else:
        cli.state.overlays_active.discard("no_bs")
    cli.save()
    status = "ON" if enable else "OFF"
    typer.echo(f"No-BS overlay set to: {status}")


@app.command("style-reading")
def style_reading(
    ctx: typer.Context,
    enable: bool = typer.Argument(
        ..., help="Enable or disable the reading overlay (on|off)"
    ),
):
    """Enable or disable the further reading overlay for the session."""
    cli: CLIContext = ctx.obj
    if isinstance(enable, str):
        enable = enable.lower() == "on"

    cli.state.reading_overlay_on = enable
    cli.save()
    status = "ON" if enable else "OFF"
    typer.echo(f"Reading overlay set to: {status}")


@app.command("style-show")
def style_show(ctx: typer.Context):
    """Show currently active overlays."""
    cli: CLIContext = ctx.obj
    active_overlays = list(cli.state.overlays_active)
    reading_status = "ON" if cli.state.reading_overlay_on else "OFF"

    if active_overlays:
        typer.echo(f"Active overlays: {', '.join(active_overlays)}")
    else:
        typer.echo("No overlays currently active")

    typer.echo(f"Reading overlay: {reading_status}")
