#!/usr/bin/env python3
import os
import pathlib
import platform
import sys
import time

import typer

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from ..core.jobs2 import JobRunner  # Phase 2
from ..core.playbooks import load_playbook, merge_defaults  # Phase 2

app = typer.Typer(help="Health checks and a synthetic Z2H smoke test")

DEFAULTS_YML = """backend: bridge
model: null
continuation:
  mode: anchor
  minChars: 3000
  pushPasses: 1
  repeatWarn: true
failover:
  watchdog_secs: 45
  max_retries: 3
  fallback_backend: openrouter
style:
  nobs: true
  narrative: true
"""


def _ensure_defaults():
    root = pathlib.Path(".xsarena")
    root.mkdir(parents=True, exist_ok=True)
    proj = root / "project.yml"
    if not proj.exists():
        proj.write_text(DEFAULTS_YML, encoding="utf-8")
        print("[doctor] created .xsarena/project.yml")
    else:
        print("[doctor] project defaults found")


def _env_report():
    print("[doctor] Environment")
    print(f"  OS: {platform.system()} {platform.release()}")
    print(f"  Python: {platform.python_version()}")
    print(f"  CWD: {os.getcwd()}")
    print(f"  OPENROUTER_API_KEY set: {'yes' if os.getenv('OPENROUTER_API_KEY') else 'no'}")


def _load_defaults():
    proj = pathlib.Path(".xsarena") / "project.yml"
    if proj.exists() and yaml:
        try:
            return yaml.safe_load(proj.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def _slug(s: str) -> str:
    import re

    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "book"


def _wait_for_job(jr: JobRunner, job_id: str, timeout: int = 600, poll: float = 2.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            j = jr.load(job_id)
        except Exception:
            time.sleep(poll)
            continue
        if j.state in ("DONE", "FAILED", "CANCELLED"):
            return j.state
        time.sleep(poll)
    return "TIMEOUT"


@app.command("run")
def doctor_run(
    subject: str = typer.Option("Doctor Smoke Test", "--subject", "-s"),
    backend: str = typer.Option(None, "--backend", "-b", help="bridge|openrouter (override defaults)"),
    max_chunks: int = typer.Option(2, "--max", help="max chunks for smoke"),
    min_chars: int = typer.Option(800, "--min", help="min chars per chunk for smoke"),
    timeout: int = typer.Option(600, "--timeout", help="timeout seconds"),
):
    """
    Run a synthetic Zero-to-Hero smoke test:
      - Create defaults if missing
      - Submit a tiny z2h job (2 chunks)
      - Wait for completion and verify artifacts
    """
    print("=== XSArena Doctor ===")
    _env_report()
    _ensure_defaults()
    defaults = _load_defaults()

    # Merge playbook + defaults + params
    pb = load_playbook("playbooks/z2h.yml")
    params = {"subject": subject, "max_chunks": max_chunks, "continuation": {"minChars": min_chars}}
    if backend:
        params["backend"] = backend
    merged = merge_defaults(pb, defaults, params)

    # Submit & wait
    jr = JobRunner(defaults)
    job_id = jr.submit(merged, params)
    print(f"[doctor] Submitted job: {job_id}")
    state = _wait_for_job(jr, job_id, timeout=timeout)
    print(f"[doctor] Job state: {state}")

    # Verify artifacts
    job_dir = pathlib.Path(".xsarena") / "jobs" / job_id
    outline = job_dir / "outline.md"
    plan = job_dir / "plan.json"
    sections_dir = job_dir / "sections"
    events = job_dir / "events.jsonl"

    slug = _slug(subject)
    final1 = pathlib.Path("books") / f"{slug}.final.md"
    final2 = pathlib.Path("books") / f"{slug}.manual.en.md"  # fallback (pre-Phase2 path)

    ok = True
    if not outline.exists():
        print("[doctor][warn] outline.md missing")
        ok = False
    if not plan.exists():
        print("[doctor][warn] plan.json missing")
        ok = False
    if not sections_dir.exists():
        print("[doctor][warn] sections/ missing")
        ok = False
    if not events.exists():
        print("[doctor][warn] events.jsonl missing")
        ok = False
    if not final1.exists() and not final2.exists():
        print("[doctor][warn] final book not found in books/")
        ok = False

    if state == "DONE" and ok:
        print("[doctor] PASS — z2h smoke test succeeded, artifacts verified.")
        sys.exit(0)
    elif state in ("FAILED", "CANCELLED", "TIMEOUT"):
        print("[doctor] FAIL — job ended in state:", state)
        sys.exit(2)
    else:
        print("[doctor] WARN — job state:", state, "artifacts ok?", ok)
        sys.exit(1)


@app.command("env")
def doctor_env():
    """Print environment and quick checks (no run)."""
    _env_report()
    _ensure_defaults()
    print("[doctor] Ready.")
