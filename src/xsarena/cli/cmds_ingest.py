import asyncio
from pathlib import Path

import typer

from .context import CLIContext

app = typer.Typer(help="Ingest and synthesize large documents.")

INGEST_SYSTEM_SYNTH = (
    """You are a synthesis engine. You will receive the previous Synthesis and a new CHUNK.
"""
    """Update the Synthesis to incorporate the new material. Keep it compact but complete:
"""
    """structured outline of topics, key claims, procedures, defaults, signature heuristics, and stylistic guidance.
"""
    """Preserve earlier coverage; merge or refactor as needed.
"""
    """Return ONLY the updated Synthesis (Markdown), no commentary, no code fences."""
)

INGEST_SYSTEM_STYLE = (
    """You are a style analysis engine. You will receive the previous Style Profile and a new CHUNK.
"""
    """Update the Style Profile to incorporate the new material's writing style, tone, and structure.
"""
    """Focus on: prose patterns, sentence structure, vocabulary choices, narrative flow, and distinctive stylistic elements.
"""
    """Preserve earlier coverage; merge or refactor as needed.
"""
    """Return ONLY the updated Style Profile (Markdown), no commentary, no code fences."""
)

INGEST_SYSTEM_ACK = (
    """You are an acknowledgment engine. You will receive a CHUNK of text.
"""
    """Acknowledge receipt of this content by briefly summarizing its main points in 1-2 sentences.
"""
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
            k = b.rfind(b"\n", i, j)
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
        f"INGEST CHUNK {i}/{n}\n\n"
        f"PREVIOUS SYNTHESIS (<= {limit_chars} chars):\n<<<SYNTHESIS\n{synth_excerpt}\nSYNTHESIS>>>\n\n"
        f"NEW CHUNK:\n<<<CHUNK\n{chunk}\nCHUNK>>>\n\n"
        f"TASK:\n"
        f"- Update the Synthesis above to fully include the NEW CHUNK's information.\n"
        f"- Keep the updated Synthesis within ~{limit_chars} characters (short, dense).\n"
        f"- Return ONLY the updated Synthesis (Markdown), no commentary.\n"
    )


def ingest_user_style(i, n, style_text, chunk, limit_chars):
    style_excerpt = (
        style_text[-limit_chars:] if len(style_text) > limit_chars else style_text
    )
    return (
        f"INGEST CHUNK {i}/{n}\n\n"
        f"PREVIOUS STYLE PROFILE (<= {limit_chars} chars):\n<<<STYLE\n{style_excerpt}\nSTYLE>>>\n\n"
        f"NEW CHUNK:\n<<<CHUNK\n{chunk}\nCHUNK>>>\n\n"
        f"TASK:\n"
        f"- Update the Style Profile above to incorporate the NEW CHUNK's writing style.\n"
        f"- Focus on prose patterns, sentence structure, vocabulary, and narrative flow.\n"
        f"- Keep the updated Style Profile within ~{limit_chars} characters (short, dense).\n"
        f"- Return ONLY the updated Style Profile (Markdown), no commentary.\n"
    )


def ingest_user_ack(i, n, chunk):
    return (
        f"INGEST CHUNK {i}/{n}\n\n"
        f"CHUNK:\n<<<CHUNK\n{chunk}\nCHUNK>>>\n\n"
        f"TASK:\n"
        f"- Acknowledge receipt of this content by briefly summarizing its main points in 1-2 sentences.\n"
        f"- Return ONLY the acknowledgment summary (plain text), no commentary.\n"
    )


@app.command("ack")
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


@app.command("synth")
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


@app.command("style")
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


@app.command("run")
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
