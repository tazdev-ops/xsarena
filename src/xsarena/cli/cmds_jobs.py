from __future__ import annotations

import asyncio
import json
import shutil
import time
from pathlib import Path

import typer

from ..core.jobs.model import JobManager, JobV3
from ..core.jobs.scheduler import Scheduler

app = typer.Typer(help="Jobs manager (list, monitor, control jobs)")


@app.command("ls")
def ls():
    """List all jobs (with totals)."""
    job_runner = JobManager()
    jobs: list[JobV3] = job_runner.list_jobs()
    sched = Scheduler()
    status = sched.get_status()

    # Get concurrency settings
    from ..core.project_config import get_project_settings

    settings = get_project_settings()

    typer.echo(
        f"Jobs: {len(jobs)} | Running: {status.get('running_jobs',0)}/{settings.concurrency.total} | Queued: {status.get('queued_jobs',0)} | Quiet: {status.get('is_quiet_time', False)}"
    )
    typer.echo(
        f"  Concurrency: Total: {settings.concurrency.total}, Bridge: {settings.concurrency.bridge}, OpenRouter: {settings.concurrency.openrouter}"
    )
    if not jobs:
        return
    # Sort by creation time, newest first
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    for j in jobs:
        typer.echo(f"{j.id}  {j.state:<10} {j.updated_at}  {j.name}")


@app.command("log")
def log(job_id: str):
    """Show the event log for a specific job."""
    path = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    if path.exists():
        typer.echo(path.read_text(encoding="utf-8"))
    else:
        typer.echo(f"No events found for job {job_id}")


@app.command("summary")
def summary(job_id: str):
    """Show a summary of a specific job."""
    job_runner = JobManager()
    try:
        job = job_runner.load(job_id)
    except FileNotFoundError:
        typer.echo(f"Error: Job '{job_id}' not found.")
        raise typer.Exit(1)

    events_path = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    chunks = retries = failovers = stalls = 0
    if events_path.exists():
        for ln in events_path.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                ev = json.loads(ln)
                t = ev.get("type")
                if t == "chunk_done":
                    chunks += 1
                elif t == "retry":
                    retries += 1
                elif t == "failover":
                    failovers += 1
                elif t == "watchdog_timeout":
                    stalls += 1
            except json.JSONDecodeError:
                continue

    typer.echo(f"Job:     {job.id}")
    typer.echo(f"State:   {job.state}")
    typer.echo(f"Name:    {job.name}")
    typer.echo(f"Created: {job.created_at}")
    typer.echo(f"Updated: {job.updated_at}")
    typer.echo(
        f"Chunks: {chunks}  Retries: {retries}  Failovers: {failovers}  Watchdogs: {stalls}"
    )


@app.command("resume")
def resume(job_id: str):
    """Resume a paused job."""
    job_runner = JobManager()
    asyncio.run(job_runner.send_control_message(job_id, "resume"))
    typer.echo(f"✅ Resume requested for job {job_id}.")


@app.command("cancel")
def cancel(job_id: str):
    """Cancel a running job."""
    job_runner = JobManager()
    asyncio.run(job_runner.send_control_message(job_id, "cancel"))
    typer.echo(f"✅ Cancel requested for job {job_id}.")


@app.command("pause")
def pause(job_id: str):
    """Pause a running job."""
    job_runner = JobManager()
    asyncio.run(job_runner.send_control_message(job_id, "pause"))
    typer.echo(f"✅ Pause requested for job {job_id}.")


@app.command("next")
def next_cmd(
    job_id: str, text: str = typer.Argument(..., help="Hint text for the next chunk")
):
    """Send a hint to override the next user prompt."""
    job_runner = JobManager()
    asyncio.run(job_runner.send_control_message(job_id, "next", text))
    typer.echo(f"✅ Next hint sent to job {job_id}: {text}")


@app.command("fork")
def fork(job_id: str, backend: str = typer.Option("openrouter", "--backend")):
    """Fork a job to a different backend (STUB)."""
    typer.echo(
        f"[jobs] Fork for job {job_id} to backend '{backend}' is not yet implemented."
    )


@app.command("watch")
def watch(
    job_id: str,
    lines: int = typer.Option(40, "--lines", "-n"),
    follow: bool = typer.Option(True, "--follow/--no-follow", "-f/-F"),
):
    """Watch the event log for a job."""
    import time

    path = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    if not path.exists():
        typer.echo(f"No events log found for job {job_id}")
        raise typer.Exit(1)

    last_pos = 0
    try:
        while True:
            with path.open("r", encoding="utf-8") as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                if new_lines:
                    for line in new_lines:
                        typer.echo(line, nl=False)
                last_pos = f.tell()
            if not follow:
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        typer.echo("\nStopped watching.")


@app.command("follow")
def follow(
    job_id: str,
    lines: int = typer.Option(200, "--lines", "-n"),
):
    """Follow the event log for a job (alias of tail -f) with graceful Ctrl-C."""
    path = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    if not path.exists():
        typer.echo(f"No events log found for job {job_id}")
        raise typer.Exit(1)

    # Go to end of file initially, or read last N lines
    with path.open("r", encoding="utf-8") as f:
        lines_list = f.readlines()
        recent_lines = lines_list[-lines:] if len(lines_list) > lines else lines_list

    # Print recent lines
    for line in recent_lines:
        typer.echo(line, nl=False)

    last_pos = path.stat().st_size  # Position at end of file

    try:
        while True:
            with path.open("r", encoding="utf-8") as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                if new_lines:
                    for line in new_lines:
                        typer.echo(line, nl=False)
                last_pos = f.tell()
            time.sleep(1.0)
    except KeyboardInterrupt:
        typer.echo("\nStopped following.")


@app.command("tail")
def tail(
    job_id: str,
    lines: int = typer.Option(200, "--lines", "-n"),
    follow: bool = typer.Option(False, "--follow/--no-follow", "-f/-F"),
):
    """Watch the event log for a job."""
    path = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    if not path.exists():
        typer.echo(f"No events log found for job {job_id}")
        raise typer.Exit(1)

    last_pos = 0
    try:
        while True:
            with path.open("r", encoding="utf-8") as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                if new_lines:
                    for line in new_lines:
                        typer.echo(line, nl=False)
                last_pos = f.tell()
            if not follow:
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        typer.echo("\nStopped watching.")


@app.command("status")
def status(job_id: str):
    """Print one-line job summary: State, chunks, retries, updated_at."""
    job_runner = JobManager()
    try:
        job = job_runner.load(job_id)
    except FileNotFoundError:
        typer.echo(f"Error: Job '{job_id}' not found.")
        raise typer.Exit(1)

    events_path = Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    chunks = retries = failovers = stalls = 0
    if events_path.exists():
        for ln in events_path.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                ev = json.loads(ln)
                t = ev.get("type")
                if t == "chunk_done":
                    chunks += 1
                elif t == "retry":
                    retries += 1
                elif t == "failover":
                    failovers += 1
                elif t == "watchdog_timeout":
                    stalls += 1
            except json.JSONDecodeError:
                continue

    typer.echo(
        f"State: {job.state}, Chunks: {chunks}, Retries: {retries}, Updated: {job.updated_at}"
    )


@app.command("boost")
def boost(
    job_id: str = typer.Argument(..., help="Job ID to boost"),
    priority: int = typer.Option(
        8, "--priority", "-p", help="New priority for the job (0-10)"
    ),
):
    """Boost the priority of a queued job."""
    from ..core.jobs.scheduler import Scheduler

    # Get the scheduler instance and update the job's priority
    scheduler = Scheduler()

    # Check if the job is in the queue
    job_found = False
    for i, (current_priority, queued_job_id) in enumerate(scheduler.job_queue):
        if queued_job_id == job_id:
            # Update the priority
            scheduler.job_queue[i] = (priority, queued_job_id)
            scheduler._sort_queue()  # Re-sort the queue
            scheduler._persist_queue()  # Persist the changes
            job_found = True
            break

    if job_found:
        typer.echo(f"✓ Priority updated for job {job_id} to {priority}")
    else:
        # Check if the job exists at all
        from ..core.jobs.model import JobManager

        job_runner = JobManager()
        try:
            job = job_runner.load(job_id)
            if job.state == "RUNNING":
                typer.echo(
                    f"⚠️  Job {job_id} is already running (cannot boost running jobs)"
                )
            else:
                typer.echo(f"⚠️  Job {job_id} is not in the queue (state: {job.state})")
        except FileNotFoundError:
            typer.echo(f"❌ Job {job_id} not found")


@app.command("gc")
def gc(
    days: int = typer.Option(30, "--days"), yes: bool = typer.Option(False, "--yes")
):
    """Garbage-collect jobs older than N days."""
    base = Path(".xsarena") / "jobs"
    if not yes:
        typer.echo(f"Would delete jobs older than {days}d. Use --yes to apply.")
        return
    now = time.time()
    deleted = 0
    if base.exists():
        for d in base.iterdir():
            if d.is_dir() and now - d.stat().st_mtime > days * 86400:
                shutil.rmtree(d, ignore_errors=True)
                deleted += 1
    typer.echo(f"Deleted {deleted} job(s)")


@app.command("rm")
def rm(job_id: str, yes: bool = typer.Option(False, "--yes")):
    """Remove a specific job directory."""
    d = Path(".xsarena") / "jobs" / job_id
    if not yes:
        typer.echo(f"Would delete {d}. Use --yes to apply.")
        return
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
        typer.echo(f"Deleted {job_id}")
    else:
        typer.echo(f"Not found: {job_id}")
