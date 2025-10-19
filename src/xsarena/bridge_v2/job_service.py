"""Job service layer for the bridge API server to decouple from JobManager."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from ..core.jobs.model import JobManager


class JobService:
    """Service layer for job operations that the bridge API server can use."""

    def __init__(self):
        self.job_manager = JobManager()

    def list_jobs(self) -> List[Dict]:
        """List all jobs with statistics."""
        jobs = self.job_manager.list_jobs()

        # Sort by creation time, newest first
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        job_list = []
        for job in jobs:
            # Get job events to calculate stats
            events_path = Path(".xsarena") / "jobs" / job.id / "events.jsonl"
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

            job_data = {
                "id": job.id,
                "name": job.name,
                "state": job.state,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "chunks": chunks,
                "retries": retries,
                "failovers": failovers,
                "stalls": stalls,
                "backend": job.backend,
            }
            job_list.append(job_data)

        return job_list

    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get a specific job's details with statistics."""
        try:
            job = self.job_manager.load(job_id)
        except FileNotFoundError:
            return None

        # Get job events to calculate stats
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

        return {
            "id": job.id,
            "name": job.name,
            "state": job.state,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "chunks": chunks,
            "retries": retries,
            "failovers": failovers,
            "stalls": stalls,
            "backend": job.backend,
            "artifacts": job.artifacts,
            "progress": job.progress,
        }
