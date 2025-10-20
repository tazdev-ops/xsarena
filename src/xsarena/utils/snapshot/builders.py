"""
Snapshot content building logic for XSArena snapshot utility.
"""

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from ..helpers import safe_read_text
from .config import ROOT


def ts_utc() -> str:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel_posix(path: Path) -> str:
    """Convert path to POSIX-style relative path."""
    return path.relative_to(ROOT).as_posix()


def sha256_bytes(b: bytes) -> str:
    """Calculate SHA256 hash of bytes."""
    return hashlib.sha256(b).hexdigest()


def build_git_context() -> str:
    """Build git context information."""
    if not (ROOT / ".git").exists():
        return "Git: (Not a git repository)\n"

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).strip()
        status_summary = (
            f"{len(status.splitlines())} changed file(s)" if status else "clean"
        )
        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci"], cwd=ROOT, text=True
        ).strip()

        return f"Git Branch: {branch}\nGit Commit: {commit}\nGit Status: {status_summary}\nGit Date: {date}\n"
    except Exception as e:
        return f"Git: (Error gathering info: {e})\n"


def build_jobs_summary() -> str:
    """Build jobs summary from .xsarena/jobs/."""
    jobs_dir = ROOT / ".xsarena" / "jobs"
    if not jobs_dir.exists():
        return "Jobs: (No jobs directory found)\n"

    summaries = []
    job_dirs = sorted(jobs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    for job_dir in job_dirs[:10]:  # Top 10 recent jobs
        if not job_dir.is_dir():
            continue
        job_file = job_dir / "job.json"
        events_file = job_dir / "events.jsonl"

        if not job_file.exists():
            continue

        try:
            job_data = json.loads(job_file.read_text("utf-8", errors="replace"))
            state = job_data.get("state", "UNKNOWN")
            name = job_data.get("name", job_dir.name)
            created_at = job_data.get("created", "N/A")
            updated_at = job_data.get("updated", "N/A")

            # Count different event types
            event_counts = {
                "chunk_done": 0,
                "retry": 0,
                "error": 0,
                "watchdog": 0,
                "failover": 0,
            }
            if events_file.exists():
                for line in events_file.read_text(
                    "utf-8", errors="replace"
                ).splitlines():
                    if '"type": "chunk_done"' in line:
                        event_counts["chunk_done"] += 1
                    elif '"type": "retry"' in line:
                        event_counts["retry"] += 1
                    elif '"type": "error"' in line:
                        event_counts["error"] += 1
                    elif '"type": "watchdog"' in line:
                        event_counts["watchdog"] += 1
                    elif '"type": "failover"' in line:
                        event_counts["failover"] += 1

            summary = f"  - {job_dir.name[:12]}: {state:<10} | Created: {created_at} | Updated: {updated_at} | "
            summary += f"Chunks: {event_counts['chunk_done']:<3} | "
            summary += f"Retries: {event_counts['retry']:<2} | "
            summary += f"Errors: {event_counts['error']:<2} | "
            summary += f"Watchdog: {event_counts['watchdog']:<2} | "
            summary += f"Failovers: {event_counts['failover']:<2} | {name}"
            summaries.append(summary)
        except Exception as e:
            summaries.append(f"  - {job_dir.name[:12]}: (Error parsing job data: {e})")

    if not summaries:
        return "Jobs: (0 jobs found)\n"

    return "Recent Jobs (top 10 most recent):\n" + "\n".join(summaries) + "\n"


def build_manifest(files: List[Path]) -> str:
    """Build a manifest of files with their sizes and hashes."""
    manifest = ["Code Manifest (files included in snapshot):"]

    for file_path in files:
        try:
            content = file_path.read_bytes()
            digest = sha256_bytes(content)
            size = len(content)
            manifest.append(
                f"  {digest[:12]}  {size:>8} bytes  {file_path.relative_to(ROOT)}"
            )
        except Exception:
            manifest.append(
                f"  {'[ERROR]':<12}  {'ERROR':>8} bytes  {file_path.relative_to(ROOT)}"
            )

    return "\n".join(manifest) + "\n"


def build_system_info() -> str:
    """Build system information."""
    info = []
    info.append(f"System: {platform.system()}")
    info.append(f"Node: {platform.node()}")
    info.append(f"Release: {platform.release()}")
    info.append(f"Version: {platform.version()}")
    info.append(f"Machine: {platform.machine()}")
    info.append(f"Processor: {platform.processor()}")
    info.append(f"Python Version: {platform.python_version()}")
    info.append(f"Python Implementation: {platform.python_implementation()}")
    info.append(f"Working Directory: {str(ROOT)}")
    try:
        import os

        info.append(f"User: {os.getlogin()}")
    except OSError:
        info.append("User: N/A")
    info.append(f"Platform: {platform.platform()}")
    return "System Information:\n" + "\n".join(info) + "\n"


def get_rules_digest() -> str:
    """Get canonical rules digest."""
    rules_file = ROOT / "directives/_rules/rules.merged.md"
    if not rules_file.exists():
        return "Rules Digest: (directives/_rules/rules.merged.md not found)\n"

    try:
        content, truncated = safe_read_text(rules_file, 10000)  # Read first 10000 chars
        lines = content.splitlines()
        first_200_lines = "\n".join(lines[:200])
        digest = sha256_bytes(first_200_lines.encode("utf-8"))

        return f"Rules Digest (SHA256 of first 200 lines of directives/_rules/rules.merged.md):\n{digest}\nFirst 200 lines preview:\n{first_200_lines}\n"
    except Exception as e:
        return f"Rules Digest: (Error reading directives/_rules/rules.merged.md: {e})\n"


def get_review_artifacts() -> str:
    """Get review artifacts if they exist."""
    review_dir = ROOT / "review"
    if not review_dir.exists():
        return "Review Artifacts: (review/ directory not found)\n"

    artifacts = []
    for item in review_dir.iterdir():
        if item.is_file():
            try:
                content, truncated = safe_read_text(
                    item, 5000
                )  # Limit to first 5000 chars
                digest = sha256_bytes(content.encode("utf-8"))
                artifacts.append(f"  {digest[:12]}  {item.name} (first 5000 chars)")
            except Exception:
                artifacts.append(f"  {'[ERROR]':<12}  {item.name}")
        elif item.is_dir():
            artifacts.append(f"  [DIR]       {item.name}/")

    return "Review Artifacts:\n" + "\n".join(artifacts) + "\n"
