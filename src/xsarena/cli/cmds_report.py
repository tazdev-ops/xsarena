# src/xsarena/cli/cmds_report.py
import time
from pathlib import Path

import typer

from ..core.jobs.model import JobManager
from ..utils.snapshot.writers import write_pro_snapshot

app = typer.Typer(help="Diagnostic reports for quick handoff or later analysis.")


def _ts():
    return time.strftime("%Y-%m-%dT%H%M%S")


def _w(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


@app.command("quick")
def quick(
    book: str = typer.Option(None, "--book"), job: str = typer.Option(None, "--job")
):
    jm = JobManager()
    lines = ["# Report (quick)", f"ts: {_ts()}"]
    if job:
        try:
            j = jm.load(job)
            lines += [f"job.id: {j.id}", f"job.state: {j.state}", f"job.name: {j.name}"]
            # crude stats
            ev = Path(".xsarena") / "jobs" / job / "events.jsonl"
            chunks = retries = watchdogs = failovers = 0
            if ev.exists():
                for ln in ev.read_text(encoding="utf-8").splitlines():
                    if '"chunk_done"' in ln:
                        chunks += 1
                    elif '"retry"' in ln:
                        retries += 1
                    elif '"watchdog"' in ln:
                        watchdogs += 1
                    elif '"failover"' in ln:
                        failovers += 1
            lines += [
                f"chunks: {chunks} retries: {retries} watchdogs: {watchdogs} failovers: {failovers}"
            ]
        except Exception as e:
            lines += [f"job.error: {e}"]
    if book:
        p = Path(book)
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            head = "\n".join(text[:120])
            tail = "\n".join(text[-120:])
            lines += ["\n## Book head (120):\n", head, "\n## Book tail (120):\n", tail]
        else:
            lines += [f"book.error: not found {book}"]
    out = Path("review") / f"report_quick_{_ts()}.md"
    _w(out, "\n".join(lines))
    typer.echo(f"→ {out}")


@app.command("job")
def job_cmd(job_id: str):
    jm = JobManager()
    j = jm.load(job_id)
    evp = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    stats = dict(chunks=0, retries=0, watchdogs=0, failovers=0)
    if evp.exists():
        for ln in evp.read_text(encoding="utf-8").splitlines():
            stats["chunks"] += '"chunk_done"' in ln
            stats["retries"] += '"retry"' in ln
            stats["watchdogs"] += '"watchdog_timeout"' in ln
            stats["failovers"] += '"failover"' in ln
    lines = [
        "# Report (job)",
        f"id: {j.id}",
        f"state: {j.state}",
        f"name: {j.name}",
        f"stats: {stats}",
    ]
    out = Path("review") / f"report_job_{job_id}.md"
    _w(out, "\n".join(map(str, lines)))
    typer.echo(f"→ {out}")


@app.command("full")
def full(book: str = typer.Option(None, "--book")):
    write_pro_snapshot(
        out_path=Path("~/xsa_debug_report.txt").expanduser(), mode="standard"
    )
    lines = ["# Report (full)", f"ts: {_ts()}", "pro snapshot: ~/xsa_debug_report.txt"]
    if book and Path(book).exists():
        lines += [f"book: {book}"]
    out = Path("review") / f"report_full_{_ts()}.md"
    _w(out, "\n".join(lines))
    typer.echo(f"→ {out}")
