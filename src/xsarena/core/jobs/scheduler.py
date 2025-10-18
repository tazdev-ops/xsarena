"""Scheduler for XSArena jobs with concurrency and quiet hours."""

import asyncio
import contextlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ...utils.io import atomic_write
from ..backends.transport import BackendTransport
from ..project_config import get_project_settings
from .model import JobManager


class Scheduler:
    """Job scheduler with concurrency control and quiet hours."""

    def __init__(
        self, max_concurrent: int = 1, quiet_hours: Optional[Dict[str, tuple]] = None
    ):
        self.max_concurrent = max_concurrent
        self.quiet_hours = quiet_hours or {}
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.job_queue: List[
            tuple[int, str]
        ] = (
            []
        )  # Queue of (priority, job ID) tuples, where lower number = higher priority
        self.transport: Optional[BackendTransport] = None
        self._project = self._load_project_cfg()
        self._project_settings = get_project_settings()

        # Initialize and load persisted queue
        self._queue_file = Path(".xsarena/ops/queue.json")
        self._load_persisted_queue()

    def _load_project_cfg(self) -> Dict[str, Any]:
        p = Path(".xsarena/project.yml")
        if p.exists():
            try:
                return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except Exception:
                return {}
        return {}

    def set_transport(self, transport: BackendTransport):
        """Set the transport for the scheduler."""
        self.transport = transport

    def is_quiet_time(self) -> bool:
        """Check if it's currently quiet hours."""
        cfg = (self._project.get("scheduler") or {}).get("quiet_hours") or {}
        if not cfg.get("enabled", False):
            return False

        now = datetime.now()
        day = now.strftime("%A").lower()
        current_hour = now.hour

        if day in cfg:
            start_hour, end_hour = (
                cfg[day]
                if isinstance(cfg[day], (list, tuple))
                else (cfg.get("start", 0), cfg.get("end", 0))
            )
            if start_hour <= current_hour < end_hour:
                return True
            elif start_hour > end_hour:  # Overnight hours (e.g., 22 to 6)
                if current_hour >= start_hour or current_hour < end_hour:
                    return True

        return False

    async def submit_job(self, job_id: str, priority: int = 5) -> bool:
        """Submit a job to the scheduler with a priority (lower number = higher priority)."""
        if self.is_quiet_time():
            # Add to queue for later processing
            self.job_queue.append((priority, job_id))
            self._sort_queue()  # Keep queue sorted by priority
            self._persist_queue()
            return True

        # Check both total and backend-specific limits
        backend_type = self._get_backend_for_job(job_id)
        backend_limit = self._get_concurrent_limit_for_backend(backend_type)
        current_backend_jobs = self._get_running_jobs_for_backend(backend_type)

        if (
            len(self.running_jobs) < self.effective_max_concurrent
            and current_backend_jobs < backend_limit
        ):
            # Run immediately
            task = asyncio.create_task(self._run_job(job_id))
            self.running_jobs[job_id] = task
            return True
        else:
            # Add to queue
            self.job_queue.append((priority, job_id))
            self._sort_queue()  # Keep queue sorted by priority
            self._persist_queue()
            return True

    def _sort_queue(self):
        """Sort the job queue by priority (lower number = higher priority)."""
        self.job_queue.sort(
            key=lambda x: x[0]
        )  # Sort by priority (first element of tuple)

    async def _run_job(self, job_id: str):
        """Internal method to run a job."""
        if not self.transport:
            raise ValueError("Transport not set for scheduler")

        # Create a job runner and run the job
        runner = JobManager()
        try:
            await runner.run_job(job_id, self.transport)
        finally:
            # Remove from running jobs when done
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]

            # Check if there are queued jobs to run
            await self._process_queue()

    async def _process_queue(self):
        """Process queued jobs if there's capacity."""
        # Process jobs that can run within limits
        remaining_queue = []
        for priority, job_id in self.job_queue:
            if self.is_quiet_time():
                remaining_queue.append(
                    (priority, job_id)
                )  # Keep in queue during quiet hours
                continue

            backend_type = self._get_backend_for_job(job_id)
            backend_limit = self._get_concurrent_limit_for_backend(backend_type)
            current_backend_jobs = self._get_running_jobs_for_backend(backend_type)

            if (
                len(self.running_jobs) < self.effective_max_concurrent
                and current_backend_jobs < backend_limit
            ):
                # Start this job
                task = asyncio.create_task(self._run_job(job_id))
                self.running_jobs[job_id] = task
            else:
                # Keep in queue
                remaining_queue.append((priority, job_id))

        self.job_queue = remaining_queue
        self._persist_queue()  # Persist the updated queue

    async def wait_for_job(self, job_id: str):
        """Wait for a specific job to complete."""
        if job_id in self.running_jobs:
            await self.running_jobs[job_id]

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id in self.running_jobs:
            task = self.running_jobs[job_id]
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            del self.running_jobs[job_id]
            return True
        else:
            # Look for the job in the priority queue
            for i, (priority, queued_job_id) in enumerate(self.job_queue):
                if queued_job_id == job_id:
                    self.job_queue.pop(i)
                    self._persist_queue()  # Persist the updated queue
                    return True
        return False

    def _get_backend_for_job(self, job_id: str) -> str:
        """Get the backend type for a specific job."""
        try:
            from .model import JobManager

            runner = JobManager()
            job = runner.load(job_id)
            return job.backend
        except Exception:
            # Default to bridge if we can't determine the backend
            return "bridge"

    def _load_persisted_queue(self):
        """Load the persisted job queue from file."""
        if self._queue_file.exists():
            try:
                import json

                content = self._queue_file.read_text(encoding="utf-8")
                data = json.loads(content)

                # Handle both old format (list of job IDs) and new format (list of [priority, job_id] tuples)
                raw_queue = data.get("queue", [])

                if not raw_queue:
                    self.job_queue = []
                    return

                # Check if this is the old format (just job IDs) or new format (priority, job_id pairs)
                if raw_queue and isinstance(raw_queue[0], str):
                    # Old format: just job IDs, assign default priority
                    self.job_queue = [(5, job_id) for job_id in raw_queue]
                elif (
                    raw_queue
                    and isinstance(raw_queue[0], list)
                    and len(raw_queue[0]) == 2
                ):
                    # New format: [priority, job_id] pairs
                    self.job_queue = [
                        (priority, job_id) for priority, job_id in raw_queue
                    ]
                else:
                    # Unexpected format, use default
                    self.job_queue = []
                    return

                # Filter out jobs that no longer exist
                valid_jobs = []
                for priority, job_id in self.job_queue:
                    try:
                        from .model import JobManager

                        runner = JobManager()
                        job = runner.load(job_id)
                        # Only keep PENDING jobs
                        if job.state == "PENDING":
                            valid_jobs.append((priority, job_id))
                    except Exception:
                        # Job doesn't exist anymore, skip it
                        continue

                self.job_queue = valid_jobs
                self._sort_queue()  # Sort by priority
            except Exception as e:
                # If there's an error loading the queue, start fresh
                print(f"Warning: Could not load persisted queue: {e}")
                self.job_queue = []

    def _persist_queue(self):
        """Persist the current job queue to file."""
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)
        import json

        # Convert priority tuples to list format for JSON serialization
        queue_for_json = [[priority, job_id] for priority, job_id in self.job_queue]

        data = {"queue": queue_for_json, "timestamp": datetime.now().isoformat()}
        atomic_write(self._queue_file, json.dumps(data, indent=2), encoding="utf-8")

    def _get_concurrent_limit_for_backend(self, backend_type: str) -> int:
        """Get the concurrent job limit for a specific backend type."""
        settings = self._project_settings
        if backend_type == "bridge":
            return settings.concurrency.bridge
        elif backend_type == "openrouter":
            return settings.concurrency.openrouter
        else:
            # Default to bridge limit for other types
            return settings.concurrency.bridge

    def _get_running_jobs_for_backend(self, backend_type: str) -> int:
        """Get the number of currently running jobs for a specific backend type."""
        count = 0
        for job_id in self.running_jobs:
            job_backend = self._get_backend_for_job(job_id)
            if job_backend == backend_type:
                count += 1
        return count

    @property
    def effective_max_concurrent(self) -> int:
        """Get the effective max concurrent jobs from config or default."""
        # For now, return the total limit
        return self._project_settings.concurrency.total

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "max_concurrent": self.effective_max_concurrent,
            "running_jobs": len(self.running_jobs),
            "queued_jobs": len(self.job_queue),
            "is_quiet_time": self.is_quiet_time(),
            "running_job_ids": list(self.running_jobs.keys()),
            "queued_job_ids": [
                job_id for priority, job_id in self.job_queue
            ],  # Just the job IDs
            "queued_jobs_with_priority": [
                [priority, job_id] for priority, job_id in self.job_queue
            ],  # Priority and job ID pairs
        }

    async def run_scheduler(self):
        """Main scheduler loop - runs indefinitely."""
        while True:
            # Process queued jobs if there's capacity
            await self._process_queue()

            # Wait before checking again
            await asyncio.sleep(1)
