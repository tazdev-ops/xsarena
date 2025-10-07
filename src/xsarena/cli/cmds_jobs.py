import os
from typing import Optional

import typer
import yaml

from ..core.jobs2 import JobRunner
from ..core.playbooks import load_playbook, merge_defaults

app = typer.Typer()


def _defaults():
    path = os.path.join(".xsarena", "project.yml")
    return yaml.safe_load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {}


@app.command("z2h")
def z2h(
    subject: str,
    out: Optional[str] = typer.Option(None, "--out"),
    max_chunks: int = typer.Option(8, "--max"),
    min_chars: int = typer.Option(3000, "--min"),
    aids: Optional[str] = typer.Option(
        None, "--aids", help="Comma-separated list of aids to generate (cram,flashcards,glossary,index)"
    ),
):
    """Zero-to-Hero command - generates comprehensive content on a topic"""
    pb = load_playbook("playbooks/z2h.yml")
    params = {
        "subject": subject,
        "io": {"outPath": out} if out else {},
        "continuation": {"minChars": min_chars},
        "max_chunks": max_chunks,
    }

    # Parse aids if provided
    if aids:
        aids_list = [aid.strip() for aid in aids.split(",")]
        params["aids"] = aids_list
        pb["aids"] = aids_list

    merged = merge_defaults(pb, _defaults(), params)
    jr = JobRunner(_defaults())
    job_id = jr.submit(merged, params)
    typer.echo(f"Submitted: {job_id}")


@app.command("run")
def run_job_cmd(job_id: str):
    """Run a job that has been submitted"""
    jr = JobRunner(_defaults())

    import threading

    def run_job_async():
        jr.run_job(job_id)

    # Run the job in a separate thread to not block the CLI
    job_thread = threading.Thread(target=run_job_async)
    job_thread.start()
    typer.echo(f"Started job: {job_id}")


@app.command("z2h-list")
def z2h_list(subjects: str, max_chunks: int = 8, min_chars: int = 3000):
    """Process multiple subjects in a list"""
    for subj in [p.strip() for p in subjects.split(";") if p.strip()]:
        z2h(subj, None, max_chunks, min_chars)


@app.command("ls")
def ls():
    """List all jobs"""
    jr = JobRunner(_defaults())
    for j in jr.list_jobs():
        typer.echo(f"{j.id}  {j.state}  {j.name}  {j.updated_at}")


@app.command("log")
def log(job_id: str):
    """Show job log events"""
    path = os.path.join(".xsarena", "jobs", job_id, "events.jsonl")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        typer.echo(f"No events found for job {job_id}")


@app.command("resume")
def resume(job_id: str):
    """Resume a job"""
    jr = JobRunner(_defaults())
    jr.resume(job_id)
    typer.echo(f"Resumed job: {job_id}")

    # If the job was in a pending state, start running it
    import threading

    def run_job_async():
        jr.run_job(job_id)

    # Run the job in a separate thread to not block the CLI
    job_thread = threading.Thread(target=run_job_async)
    job_thread.start()
    typer.echo(f"Started running job: {job_id}")


@app.command("cancel")
def cancel(job_id: str):
    """Cancel a job"""
    jr = JobRunner(_defaults())
    jr.cancel(job_id)
    typer.echo(f"Cancelled job: {job_id}")


@app.command("fork")
def fork(
    job_id: str, backend: Optional[str] = typer.Option(None, "--backend", help="Backend to use for the forked job")
):
    """Fork a job (clone with optional backend change)"""
    jr = JobRunner(_defaults())
    original_job = jr.load(job_id)

    # Create a transplant summary for the new job
    transplant_summary = jr._create_transplant_summary(job_id)

    # Create a new job based on the original
    import uuid

    new_job_id = str(uuid.uuid4())

    # Update the backend if specified
    new_backend = backend if backend else original_job.backend
    new_params = original_job.params.copy()
    if backend:
        new_params["backend"] = backend

    # Create new job object
    from datetime import datetime

    from ..core.jobs2 import Job

    new_job = Job(
        id=new_job_id,
        name=original_job.name,
        playbook=original_job.playbook,
        params=new_params,
        backend=new_backend,
        state="PENDING",
        retries=original_job.retries,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        artifacts=original_job.artifacts.copy(),
        meta=original_job.meta.copy(),
    )

    # Create job directory
    job_dir = os.path.join(".xsarena", "jobs", new_job_id)
    os.makedirs(job_dir, exist_ok=True)

    # Save job.json
    job_path = os.path.join(job_dir, "job.json")
    import json

    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "id": new_job.id,
                "name": new_job.name,
                "playbook": new_job.playbook,
                "params": new_job.params,
                "backend": new_job.backend,
                "state": new_job.state,
                "retries": new_job.retries,
                "created_at": new_job.created_at,
                "updated_at": new_job.updated_at,
                "artifacts": new_job.artifacts,
                "meta": new_job.meta,
            },
            f,
            indent=2,
        )

    # Create events.jsonl
    events_path = os.path.join(job_dir, "events.jsonl")
    with open(events_path, "w", encoding="utf-8") as f:
        event = {
            "ts": datetime.now().isoformat(),
            "type": "job_forked",
            "job_id": new_job_id,
            "original_job_id": job_id,
            "backend": backend,
        }
        f.write(json.dumps(event) + "\n")

    # Add transplant summary to the new job's meta or system text
    # This will be used when the job continues
    if transplant_summary:
        # Add to meta to be used by the engine
        new_job.meta["transplant_summary"] = transplant_summary
        # Update job.json with meta
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "id": new_job.id,
                    "name": new_job.name,
                    "playbook": new_job.playbook,
                    "params": new_job.params,
                    "backend": new_job.backend,
                    "state": new_job.state,
                    "retries": new_job.retries,
                    "created_at": new_job.created_at,
                    "updated_at": new_job.updated_at,
                    "artifacts": new_job.artifacts,
                    "meta": new_job.meta,
                },
                f,
                indent=2,
            )

    # Create checkpoints dir
    checkpoints_dir = os.path.join(job_dir, "checkpoints")
    os.makedirs(checkpoints_dir, exist_ok=True)

    typer.echo(f"Forked job: {job_id} -> {new_job_id}")


@app.command("open")
def open_cmd(job_id: str):
    """Open the job's artifacts folder"""
    import subprocess
    import sys

    job_dir = os.path.join(".xsarena", "jobs", job_id)
    if not os.path.exists(job_dir):
        typer.echo(f"Job {job_id} not found")
        return

    try:
        if sys.platform.startswith("darwin"):  # macOS
            subprocess.run(["open", job_dir], check=True)
        elif sys.platform.startswith("win"):  # Windows
            subprocess.run(["explorer", job_dir], check=True)
        else:  # Linux and other Unix-like
            subprocess.run(["xdg-open", job_dir], check=True)
    except subprocess.CalledProcessError:
        typer.echo(f"Failed to open folder: {job_dir}")
    except FileNotFoundError:
        typer.echo(f"Could not open folder: {job_dir} (folder does not exist)")


@app.command("summary")
def summary(job_id: str):
    """Show job summary with chunks, stalls, retries, failovers, total tokens/cost, elapsed time"""
    import json
    from pathlib import Path

    job_dir = Path(".xsarena") / "jobs" / job_id
    if not job_dir.exists():
        typer.echo(f"Job {job_id} not found")
        return

    # Load job.json to get basic info
    job_path = job_dir / "job.json"
    if not job_path.exists():
        typer.echo(f"Job {job_id} has no job.json")
        return

    try:
        with open(job_path, "r", encoding="utf-8") as f:
            job_data = json.load(f)

        # Load events.jsonl to get detailed metrics
        events_path = job_dir / "events.jsonl"
        if not events_path.exists():
            typer.echo(f"Job {job_id} has no events.jsonl")
            return

        events = []
        total_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        chunks_done = 0
        retries = 0
        failovers = 0
        stalls = 0
        start_time = None
        end_time = None
        lint_warnings = 0

        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        events.append(event)

                        # Calculate metrics
                        if event.get("type") == "job_submitted" and not start_time:
                            start_time = event.get("ts")
                        elif event.get("type") in ["job_completed", "job_failed", "job_cancelled", "job_ended"]:
                            end_time = event.get("ts")

                        if event.get("type") == "chunk_done":
                            chunks_done += 1
                        elif event.get("type") == "retry":
                            retries += 1
                        elif event.get("type") == "failover":
                            failovers += 1
                        elif event.get("type") == "watchdog_timeout":
                            stalls += 1
                        elif event.get("type") == "cost":
                            total_cost += event.get("est_usd", 0)
                            total_input_tokens += event.get("input_tokens", 0)
                            total_output_tokens += event.get("output_tokens", 0)
                        elif event.get("type") == "lint_warning":
                            lint_warnings += 1
                    except json.JSONDecodeError:
                        continue

        # Calculate elapsed time
        elapsed_time = None
        if start_time and end_time:
            from datetime import datetime

            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                elapsed_time = end_dt - start_dt
            except ValueError:
                # Handle if datetime format is different
                pass
        elif start_time:
            # Job is still running
            from datetime import datetime

            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end_dt = datetime.now()
            elapsed_time = end_dt - start_dt

        # Print summary
        typer.echo(f"Job Summary for: {job_id}")
        typer.echo(f"  State: {job_data.get('state', 'unknown')}")
        typer.echo(f"  Subject: {job_data.get('params', {}).get('subject', 'N/A')}")
        typer.echo(f"  Backend: {job_data.get('backend', 'unknown')}")
        typer.echo(f"  Chunks: {chunks_done}")
        typer.echo(f"  Stalls: {stalls}")
        typer.echo(f"  Retries: {retries}")
        typer.echo(f"  Failovers: {failovers}")
        typer.echo(f"  Lint Warnings: {lint_warnings}")
        typer.echo(
            f"  Total tokens: {total_input_tokens} input + {total_output_tokens} output = {total_input_tokens + total_output_tokens}"
        )
        typer.echo(f"  Estimated cost: ${total_cost:.6f}")
        typer.echo(f"  Elapsed time: {elapsed_time if elapsed_time else 'N/A'}")

    except Exception as e:
        typer.echo(f"Error reading job data: {e}")


@app.command("budget")
def jobs_budget(job_id: str, usd: float):
    from ..core.jobs2 import JobRunner

    jr = JobRunner({})
    jr.set_budget(job_id, float(usd))
    typer.echo(f"[jobs] budget set: {usd:.2f} USD")


@app.command("pause")
def jobs_pause(job_id: str):
    from ..core.jobs2 import JobRunner

    JobRunner({}).cancel(job_id)
    typer.echo("[jobs] paused.")


@app.command("resume")
def jobs_resume(job_id: str):
    from ..core.jobs2 import JobRunner

    JobRunner({}).resume(job_id)
    typer.echo("[jobs] resumed.")


@app.command("fork")
def jobs_fork(job_id: str, backend: str = "openrouter"):
    from ..core.jobs2 import JobRunner

    new_id = JobRunner({}).fork(job_id, backend=backend)
    typer.echo(f"[jobs] forked → {new_id}")


@app.command("watch")
def jobs_watch(job_id: str, lines: int = 40, follow: bool = True):
    import pathlib
    import time

    path = pathlib.Path(".xsarena") / "jobs" / job_id / "events.jsonl"
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
