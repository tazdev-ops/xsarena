# src/xsarena/cli/cmds_handoff.py
import time
from pathlib import Path

import typer

from ..core.jobs.model import JobManager
from ..utils.snapshot.writers import write_text_snapshot

app = typer.Typer(help="Prepare a clean handoff package for higher AI.")


def _ts():
    return time.strftime("%Y-%m-%dT%H%M%S")


def _dir():
    d = Path("review") / "handoff" / f"handoff_{_ts()}"
    d.mkdir(parents=True, exist_ok=True)
    return d


@app.command("prepare")
def prepare(
    book: str = typer.Option(None, "--book"),
    job: str = typer.Option(None, "--job"),
    note: str = typer.Option("", "--note"),
):
    base = _dir()
    # 1) Flat snapshot (tight, redacted)
    snap_path = Path("~/repo_flat.txt").expanduser()
    write_text_snapshot(
        out_path=snap_path,
        mode="minimal",
        with_git=False,
        with_jobs=False,
        with_manifest=False,
        include_system=False,
        dry_run=False,
    )
    # 2) Brief
    lines = [
        "# Handoff Request",
        f"ts: {_ts()}",
        f"book: {book or '(none)'}",
        f"job: {job or '(none)'}",
        f"snapshot: {snap_path}",
        "",
        "## Problem",
        note or "(fill in)",
        "",
        "## Expected vs Actual",
        "- Expected: ...",
        "- Actual: ...",
        "",
        "## Repro Steps",
        "1) ...",
        "2) ...",
        "",
        "## Attachments",
        f"- snapshot: {snap_path}",
    ]
    brief = base / "handoff_request.md"
    brief.write_text("\n".join(lines), encoding="utf-8")
    # Optional samples
    if book and Path(book).exists():
        bp = Path(book)
        head = "\n".join(
            bp.read_text(encoding="utf-8", errors="ignore").splitlines()[:120]
        )
        (base / "book_head.md").write_text(head, encoding="utf-8")
    if job:
        try:
            jm = JobManager()
            j = jm.load(job)
            (base / "job.json").write_text(
                j.model_dump_json(indent=2), encoding="utf-8"
            )
        except Exception:
            pass
    typer.echo(f"→ {brief}")


@app.command("note")
def add_note(text: str):
    root = Path("review") / "handoff"
    dirs = sorted([p for p in root.glob("handoff_*") if p.is_dir()], reverse=True)
    if not dirs:
        typer.echo("No handoff folder found.")
        raise typer.Exit(1)
    brief = dirs[0] / "handoff_request.md"
    with brief.open("a", encoding="utf-8") as f:
        f.write(f"\n- NOTE { _ts() }: {text}\n")
    typer.echo(f"✓ noted → {brief}")


@app.command("show")
def show():
    root = Path("review") / "handoff"
    dirs = sorted([p for p in root.glob("handoff_*") if p.is_dir()], reverse=True)
    if not dirs:
        typer.echo("No handoff folder found.")
        raise typer.Exit(1)
    latest = dirs[0]
    typer.echo(str(latest))
    for p in latest.iterdir():
        typer.echo(f"  - {p.name}")
