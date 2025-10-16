from __future__ import annotations

import json
import tarfile
import time
from pathlib import Path
from typing import Optional

import typer

from ..core.redact import redact
from .context import CLIContext

app = typer.Typer(help="Create a redacted report bundle for higher AI")


def _ts() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _write(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _read(p: Path, max_bytes: int = 200_000) -> str:
    try:
        data = p.read_bytes()
    except Exception:
        return ""
    if len(data) > max_bytes:
        half = max_bytes // 2
        data = data[:half] + b"\n\n[...TRUNCATED...]\n\n" + data[-half:]
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return data.decode("latin-1", errors="replace")


def _latest_job_id() -> Optional[str]:
    jobs = Path(".xsarena/jobs")
    if not jobs.exists():
        return None
    dirs = sorted(
        [d for d in jobs.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return dirs[0].name if dirs else None


def _summarize_events(job_dir: Path) -> dict:
    evp = job_dir / "events.jsonl"
    out = {
        "chunks": 0,
        "retries": 0,
        "failovers": 0,
        "watchdogs": 0,
        "first_ts": "",
        "last_ts": "",
    }
    if not evp.exists():
        return out
    first = last = ""
    for line in evp.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        t = ev.get("type")
        ts = ev.get("ts", "")
        if not first:
            first = ts
        if ts:
            last = ts
        if t == "chunk_done":
            out["chunks"] += 1
        elif t == "retry":
            out["retries"] += 1
        elif t == "failover":
            out["failovers"] += 1
        elif t == "watchdog_timeout":
            out["watchdogs"] += 1
    out["first_ts"], out["last_ts"] = first, last
    return out


def _pack(folder: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest, "w:gz") as tar:
        tar.add(folder, arcname=folder.name)


def _header(kind: str) -> str:
    return (
        f"# XSArena Report ({kind})\n\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S')}\nNote: Redacted bundle.\n\n"
        "## Include in your message\n- Command used\n- Expected vs actual\n- Attach this tar.gz\n"
    )


def _common(
    root: Path, cli: CLIContext, job_id: Optional[str], book_path: Optional[str]
):
    _write(root / "report.md", _header("bundle"))
    cfg = Path(".xsarena/config.yml")
    sst = Path(".xsarena/session_state.json")
    if cfg.exists():
        _write(root / "config.yml", redact(_read(cfg)))
    if sst.exists():
        _write(root / "session_state.json", redact(_read(sst)))
    for f in ["pyproject.toml", "README.md"]:
        fp = Path(f)
        if_exists = fp.exists()
        if if_exists:
            _write(root / f, redact(_read(fp)))
    rules = Path("directives/_rules/rules.merged.md")
    if rules.exists():
        _write(root / "rules.merged.md", redact(_read(rules)))
    if book_path:
        bp = Path(book_path)
        if bp.exists():
            _write(root / "book_sample.md", _read(bp, 300_000))
    if job_id:
        jd = Path(".xsarena/jobs") / job_id
        if jd.exists():
            _write(root / "job.json", redact(_read(jd / "job.json")))
            _write(root / "events.jsonl", redact(_read(jd / "events.jsonl", 300_000)))
            _write(
                root / "job_summary.json", json.dumps(_summarize_events(jd), indent=2)
            )


@app.command("quick")
def report_quick(
    ctx: typer.Context,
    book: Optional[str] = typer.Option(
        None, "--book", help="Attach head/tail sample from this book file"
    ),
):
    cli: CLIContext = ctx.obj
    rid = _ts()
    outdir = Path("review") / f"report_{rid}"
    outdir.mkdir(parents=True, exist_ok=True)
    _common(outdir, cli, _latest_job_id(), book)
    tar = Path("review") / f"report_{rid}.tar.gz"
    _pack(outdir, tar)
    typer.echo(f"[report] quick → {tar}")


@app.command("job")
def report_job(
    ctx: typer.Context,
    job_id: str = typer.Argument(...),
    book: Optional[str] = typer.Option(None, "--book"),
):
    cli: CLIContext = ctx.obj
    rid = _ts()
    outdir = Path("review") / f"report_{rid}"
    outdir.mkdir(parents=True, exist_ok=True)
    _common(outdir, cli, job_id, book)
    tar = Path("review") / f"report_{rid}.tar.gz"
    _pack(outdir, tar)
    typer.echo(f"[report] job {job_id} → {tar}")


@app.command("full")
def report_full(
    ctx: typer.Context,
    include_recipes: bool = typer.Option(True, "--recipes/--no-recipes"),
    include_directives: bool = typer.Option(False, "--directives/--no-directives"),
    book: Optional[str] = typer.Option(None, "--book"),
):
    cli: CLIContext = ctx.obj
    rid = _ts()
    outdir = Path("review") / f"report_{rid}"
    outdir.mkdir(parents=True, exist_ok=True)
    _common(outdir, cli, _latest_job_id(), book)
    if include_recipes:
        for p in Path("recipes").rglob("*.yml"):
            try:
                _write(outdir / "recipes" / p.name, redact(_read(p, 120_000)))
            except Exception:
                pass
    if include_directives:
        for p in Path("directives").rglob("*"):
            if (
                p.is_file()
                and p.suffix in {".md", ".txt"}
                and p.stat().st_size < 200_000
            ):
                try:
                    _write(
                        outdir / "directives" / p.relative_to("directives"),
                        redact(_read(p, 120_000)),
                    )
                except Exception:
                    pass
    tar = Path("review") / f"report_{rid}.tar.gz"
    _pack(outdir, tar)
    typer.echo(f"[report] full → {tar}")


from pathlib import Path as _Path


@app.command("handoff")
def handoff(
    book: str = typer.Option(None, "--book", help="Optional path to a relevant book"),
    outdir: str = typer.Option("docs/handoff", help="Output directory"),
):
    """Create a handoff file for higher AI with snapshot digest and context."""
    out_dir = _Path(outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"HANDOFF_{ts}.md"

    snap = _Path(".xsarena/snapshots/final_snapshot.txt")
    digest = ""
    if snap.exists():
        import hashlib

        digest = hashlib.sha256(snap.read_bytes()).hexdigest()

    head = []
    if book:
        try:
            b = _Path(book)
            if b.exists():
                text = b.read_text(encoding="utf-8", errors="replace")
                head = [text[:1200], text[-1200:]] if len(text) > 2400 else [text]
        except Exception:
            pass

    body = f"""# Handoff
Branch: (git rev-parse --abbrev-ref HEAD)
Snapshot digest (sha256 of final_snapshot.txt): {digest or '(none)'}
Commands run:
Expected vs Actual:
Errors/Logs:
Job ID/context (if any):
Ask:

## Book sample
{(''.join(['\n--- head ---\n', head[0], '\n--- tail ---\n', head[1]]) if len(head)==2 else (head[0] if head else '(none)'))}
"""
    path.write_text(body, encoding="utf-8")
    typer.echo(f"[OK] Handoff written → {path}")
