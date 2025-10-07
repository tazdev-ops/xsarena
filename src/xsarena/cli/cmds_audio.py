#!/usr/bin/env python3
import asyncio
import os
import pathlib
import shutil
from typing import Optional

import typer

app = typer.Typer(help="Convert EPUB to audiobook (Edge TTS by default)")


def _jobs_root():
    return pathlib.Path(".xsarena") / "jobs"


def _books_root():
    return pathlib.Path("books")


def find_epub_for_job(jid: str) -> Optional[pathlib.Path]:
    # Prefer books/<slug>.epub; else suggest publish
    job_json = _jobs_root() / jid / "job.json"
    if not job_json.exists():
        return None
    import json
    import re

    data = json.loads(job_json.read_text(encoding="utf-8"))
    subj = data.get("params", {}).get("subject") or data.get("playbook", {}).get("subject") or "book"
    slug = re.sub(r"[^a-z0-9]+", "-", subj.lower()).strip("-") or "book"
    ep = _books_root() / f"{slug}.epub"
    return ep if ep.exists() else None


async def synth_edge(
    epub_path: pathlib.Path,
    outdir: pathlib.Path,
    voice: str,
    fmt: str,
    rate: str,
    vol: str,
    pitch: str,
    break_ms: int,
    language: Optional[str] = None,
):
    # parse epub → [(title, text)], then synthesize via edge-tts
    import edge_tts
    from bs4 import BeautifulSoup
    from ebooklib import epub

    outdir.mkdir(parents=True, exist_ok=True)
    book = epub.read_epub(str(epub_path))
    chapters = []
    for item in book.get_items():
        if item.get_type() == 9:  # ITEM_DOCUMENT
            html = item.get_content()
            soup = BeautifulSoup(html, "html.parser")
            title = (
                soup.title.string.strip()
                if soup.title
                else (soup.h1.get_text(strip=True) if soup.h1 else f"Chapter {len(chapters)+1}")
            )
            # crude text extraction; agent can refine
            text = soup.get_text("\n")
            if text.strip():
                chapters.append((title, text))
    idx = 1
    for title, text in chapters:
        safe = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "-")[:80]
        outfile = outdir / f"{idx:04d}-{safe}.{fmt}"
        # You can segment text by paragraphs; simple pass here:
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, volume=vol, pitch=pitch)
        await communicate.save(str(outfile))
        idx += 1
    return len(chapters)


def run_external(
    epub_path: pathlib.Path, outdir: pathlib.Path, voice: str, language: Optional[str], fmt: str, break_ms: int
):
    bin_name = (
        os.getenv("XSA_E2A_BIN") or shutil.which("epub_to_audiobook") or shutil.which("epub-to-audiobook") or None
    )
    if not bin_name:
        typer.echo("External tool not found. Falling back to edge.", err=True)
        return None
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        bin_name,
        str(epub_path),
        str(outdir),
        "--tts",
        "edge",
        "--voice_name",
        voice,
        "--output_format",
        fmt,
        "--break_duration",
        str(break_ms),
        "--no_prompt",
    ]
    if language:
        cmd += ["--language", language]
    import subprocess

    return subprocess.run(cmd).returncode


@app.command("run")
def audio_run(
    target: str = typer.Argument(..., help="<job_id> or path to .epub"),
    provider: str = typer.Option("edge", "--provider", "-p", help="edge|external"),
    voice: str = typer.Option("en-US-JennyNeural", "--voice"),
    language: Optional[str] = typer.Option(None, "--language"),
    fmt: str = typer.Option("mp3", "--format"),
    rate: str = typer.Option("+0%", "--rate"),
    volume: str = typer.Option("+0%", "--volume"),
    pitch: str = typer.Option("+0Hz", "--pitch"),
    break_ms: int = typer.Option(1250, "--break-ms"),
    outdir: str = typer.Option("./audio", "--outdir"),
):
    outdir_p = pathlib.Path(outdir)
    p = pathlib.Path(target)
    if p.suffix.lower() == ".epub" and p.exists():
        epub_path = p
    else:
        epub_path = find_epub_for_job(target)
        if not epub_path:
            typer.echo("No EPUB found. Run: xsarena publish run <job_id> --epub", err=True)
            raise typer.Exit(1)

    if provider == "external":
        rc = run_external(epub_path, outdir_p, voice, language, fmt, break_ms)
        if rc == 0:
            typer.echo(f"[audio] External conversion ok → {outdir}")
            raise typer.Exit(0)
        else:
            typer.echo("[audio] External tool failed; falling back to edge.", err=True)

    # edge fallback
    try:
        asyncio.run(synth_edge(epub_path, outdir_p, voice, fmt, rate, volume, pitch, break_ms, language))
        typer.echo(f"[audio] Edge TTS ok → {outdir}")
    except ModuleNotFoundError as e:
        typer.echo(f"Missing module: {e}. Install extras: pip install -e '.[audio]'", err=True)
        raise typer.Exit(2)


@app.command("preview")
def audio_preview(target: str, voice: str = "en-US-JennyNeural", fmt: str = "mp3"):
    """Generate audio preview from first chapter only"""
    outdir_p = pathlib.Path("./audio")
    p = pathlib.Path(target)
    if p.suffix.lower() == ".epub" and p.exists():
        epub_path = p
    else:
        epub_path = find_epub_for_job(target)
        if not epub_path:
            typer.echo("No EPUB found. Run: xsarena publish run <job_id> --epub", err=True)
            raise typer.Exit(1)

    # parse epub and get only the first chapter
    import edge_tts
    from bs4 import BeautifulSoup
    from ebooklib import epub

    outdir_p.mkdir(parents=True, exist_ok=True)
    book = epub.read_epub(str(epub_path))
    first_chapter = None

    for item in book.get_items():
        if item.get_type() == 9:  # ITEM_DOCUMENT
            html = item.get_content()
            soup = BeautifulSoup(html, "html.parser")
            title = (
                soup.title.string.strip() if soup.title else (soup.h1.get_text(strip=True) if soup.h1 else "Chapter 1")
            )
            text = soup.get_text("\n")
            if text.strip() and not first_chapter:
                first_chapter = (title, text)
                break

    if first_chapter:
        title, text = first_chapter
        safe = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "-")[:80]
        outfile = outdir_p / f"preview_0001-{safe}.{fmt}"

        # Synthesize only the first chapter
        communicate = edge_tts.Communicate(text, voice=voice)
        asyncio.run(communicate.save(str(outfile)))

        typer.echo(f"[audio] Preview generated → {outfile}")
    else:
        typer.echo("[audio] No chapters found in EPUB", err=True)
        raise typer.Exit(1)
