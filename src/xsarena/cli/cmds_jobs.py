from __future__ import annotations

import json
import os

import typer
import yaml

from ..core.jobs2_runner import JobRunner

app = typer.Typer(help="Jobs runner (recipes, fast runs, summaries)")


def _defaults():
    path = os.path.join(".xsarena", "project.yml")
    return (
        yaml.safe_load(open(path, "r", encoding="utf-8"))
        if os.path.exists(path)
        else {}
    )


def _load_yaml_or_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith((".yml", ".yaml")):
            return yaml.safe_load(f) or {}
        return json.load(f)


@app.command("run")
def jobs_run(
    file: str = typer.Argument(..., help="Recipe file (.yml/.yaml/.json)"),
    apply: bool = typer.Option(True, "--apply/--dry-run", help="Execute job (default: execute)"),
):
    """DEPRECATED: Use 'xsarena run from-recipe' instead."""
    typer.echo("⚠️  DEPRECATED: Use 'xsarena run from-recipe' instead.")
    
    # Call the new run from-recipe command
    typer.echo(f"Would run recipe from: {file}")
    typer.echo("Please use 'xsarena run from-recipe' with appropriate parameters instead.")


@app.command("ls")
def ls():
    jr = JobRunner(_defaults())
    for j in jr.list_jobs():
        typer.echo(f"{j.id}  {j.state}  {j.name}  {j.updated_at}")


@app.command("log")
def log(job_id: str):
    path = os.path.join(".xsarena", "jobs", job_id, "events.jsonl")
    if os.path.exists(path):
        print(open(path, "r", encoding="utf-8").read())
    else:
        typer.echo(f"No events found for {job_id}")


@app.command("summary")
def summary(job_id: str):
    from pathlib import Path

    job_dir = Path(".xsarena") / "jobs" / job_id
    job_path = job_dir / "job.json"
    events_path = job_dir / "events.jsonl"
    if not job_path.exists():
        typer.echo("job.json missing")
        raise typer.Exit(1)
    job = json.load(open(job_path, "r", encoding="utf-8"))
    if not events_path.exists():
        typer.echo("events.jsonl missing")
        raise typer.Exit(1)
    chunks = 0
    retries = 0
    failovers = 0
    stalls = 0
    for ln in open(events_path, "r", encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        t = ev.get("type")
        chunks += 1 if t == "chunk_done" else 0
        retries += 1 if t == "retry" else 0
        failovers += 1 if t == "failover" else 0
        stalls += 1 if t == "watchdog_timeout" else 0
    typer.echo(f"Job: {job_id}  State: {job.get('state','?')}")
    typer.echo(f"Subject: {job.get('playbook',{}).get('subject','N/A')}")
    typer.echo(
        f"Chunks: {chunks}  Retries: {retries}  Failovers: {failovers}  Watchdogs: {stalls}"
    )


@app.command("resume")
def resume(job_id: str):
    JobRunner(_defaults()).resume(job_id)
    typer.echo("[jobs] resume requested (stub).")


@app.command("cancel")
def cancel(job_id: str):
    JobRunner(_defaults()).cancel(job_id)
    typer.echo("[jobs] cancel requested (stub).")


@app.command("fork")
def fork(job_id: str, backend: str = typer.Option("openrouter", "--backend")):
    new_id = JobRunner(_defaults()).fork(job_id, backend=backend)
    typer.echo(f"[jobs] forked → {new_id}")


@app.command("watch")
def watch(job_id: str, lines: int = 40, follow: bool = True):
    import time
    from pathlib import Path

    path = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    if not path.exists():
        typer.echo("No events.jsonl")
        raise typer.Exit(1)
    last = 0
    while True:
        txt = path.read_text(encoding="utf-8").splitlines()
        new = txt[-lines:] if last == 0 else txt[last:]
        for ln in new:
            print(ln)
        last = len(txt)
        if not follow:
            break
        time.sleep(1.0)
