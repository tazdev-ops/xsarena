"""Job persistence layer for XSArena v0.3."""

import contextlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...utils.helpers import load_json_with_error_handling
from ...utils.io import atomic_write
from .model import JobV3


def load_json(path: Path) -> dict:
    """Helper to load JSON with error handling."""
    return load_json_with_error_handling(path)


class JobStore:
    """Handles job persistence operations (load/save/list)."""

    def __init__(self):
        Path(".xsarena/jobs").mkdir(parents=True, exist_ok=True)

    def _job_dir(self, job_id: str) -> Path:
        """Get the directory for a job."""
        return Path(".xsarena") / "jobs" / job_id

    def _get_last_completed_chunk(self, job_id: str) -> int:
        """Get the index of the last completed chunk by parsing events.jsonl."""
        events_path = self._job_dir(job_id) / "events.jsonl"
        if not events_path.exists():
            return 0

        last_chunk_idx = 0
        try:
            with open(events_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line.strip())
                            if (
                                event.get("type") == "chunk_done"
                                and "chunk_idx" in event
                            ):
                                chunk_idx = event["chunk_idx"]
                                if chunk_idx > last_chunk_idx:
                                    last_chunk_idx = chunk_idx
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass  # If we can't read the file, return 0

        return last_chunk_idx

    def load(self, job_id: str) -> JobV3:
        """Load a job by ID."""
        job_path = self._job_dir(job_id) / "job.json"
        data = load_json(job_path)
        return JobV3(**data)

    def save(self, job: JobV3):
        """Save job metadata."""
        jd = self._job_dir(job.id)
        job_path = jd / "job.json"
        atomic_write(job_path, json.dumps(job.model_dump(), indent=2), encoding="utf-8")

    def list_all(self) -> List[JobV3]:
        """List all jobs."""
        base = Path(".xsarena") / "jobs"
        out: List[JobV3] = []
        if not base.exists():
            return out
        for d in base.iterdir():
            p = d / "job.json"
            if p.exists():
                out.append(self.load(d.name))
        return out

    def _log_event(self, job_id: str, ev: Dict[str, Any]):
        """Log an event for a job with standardized structure."""
        ev_path = self._job_dir(job_id) / "events.jsonl"
        # Ensure standard fields are present according to schema {ts, type, job_id, chunk_idx?, bytes?, hint?, attempt?, status_code?}
        standardized_event = {
            "ts": self._ts(),
            "type": ev.get("type", "unknown"),
            "job_id": job_id,
        }
        # Add optional fields from the original event if they exist
        for key in ["chunk_idx", "bytes", "hint", "attempt", "status_code"]:
            if key in ev:
                standardized_event[key] = ev[key]

        # Add any other fields from the original event
        for key, value in ev.items():
            if key not in standardized_event:
                standardized_event[key] = value

        # Use direct file operations with flush/fsync for durability
        with open(ev_path, "a", encoding="utf-8") as e:
            e.write(json.dumps(standardized_event) + "\n")
            e.flush()
            with contextlib.suppress(Exception):
                os.fsync(e.fileno())

    @staticmethod
    def _ts() -> str:
        """Get current timestamp."""
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def find_resumable(self, out_path_abs: str) -> Optional[str]:
        """Find an existing job (not DONE/FAILED/CANCELLED) that targets out_path."""
        target = os.path.abspath(out_path_abs)
        for job in self.list_all():
            job_out = self._normalize_out(job.run_spec)
            if job_out == target and job.state not in ("DONE", "FAILED", "CANCELLED"):
                return job.id
        return None

    def _normalize_out(self, run_spec) -> str:
        """Mirror how run spec/out_path is constructed in orchestrator/run."""
        base = (
            run_spec.out_path
            or f"./books/{run_spec.subject.replace(' ', '_')}.final.md"
        )
        return os.path.abspath(base)
