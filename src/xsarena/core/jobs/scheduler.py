"""Scheduler for XSArena jobs with concurrency and quiet hours."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..backends.transport import BackendTransport
from .model import JobRunnerV3


class Scheduler:
    """Job scheduler with concurrency control and quiet hours."""

    def __init__(
        self, max_concurrent: int = 1, quiet_hours: Optional[Dict[str, tuple]] = None
    ):
        self.max_concurrent = max_concurrent
        self.quiet_hours = quiet_hours or {}  # e.g., {"monday": (22, 6)} for 10PM-6AM
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.job_queue: List[str] = []  # Queue of job IDs to run
        self.transport: Optional[BackendTransport] = None

    def set_transport(self, transport: BackendTransport):
        """Set the transport for the scheduler."""
        self.transport = transport

    def is_quiet_time(self) -> bool:
        """Check if it's currently quiet hours."""
        if not self.quiet_hours:
            return False

        now = datetime.now()
        day = now.strftime("%A").lower()
        current_hour = now.hour

        if day in self.quiet_hours:
            start_hour, end_hour = self.quiet_hours[day]
            if start_hour <= current_hour < end_hour:
                return True
            elif start_hour > end_hour:  # Overnight hours (e.g., 22 to 6)
                if current_hour >= start_hour or current_hour < end_hour:
                    return True

        return False

    async def submit_job(self, job_id: str) -> bool:
        """Submit a job to the scheduler."""
        if self.is_quiet_time():
            # Add to queue for later processing
            self.job_queue.append(job_id)
            return True

        if len(self.running_jobs) < self.max_concurrent:
            # Run immediately
            task = asyncio.create_task(self._run_job(job_id))
            self.running_jobs[job_id] = task
            return True
        else:
            # Add to queue
            self.job_queue.append(job_id)
            return True

    async def _run_job(self, job_id: str):
        """Internal method to run a job."""
        if not self.transport:
            raise ValueError("Transport not set for scheduler")

        # Create a job runner and run the job
        runner = JobRunnerV3()
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
        while self.job_queue and len(self.running_jobs) < self.max_concurrent:
            if self.is_quiet_time():
                break  # Don't process during quiet hours

            job_id = self.job_queue.pop(0)
            task = asyncio.create_task(self._run_job(job_id))
            self.running_jobs[job_id] = task

    async def wait_for_job(self, job_id: str):
        """Wait for a specific job to complete."""
        if job_id in self.running_jobs:
            await self.running_jobs[job_id]

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id in self.running_jobs:
            task = self.running_jobs[job_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.running_jobs[job_id]
            return True
        elif job_id in self.job_queue:
            self.job_queue.remove(job_id)
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "max_concurrent": self.max_concurrent,
            "running_jobs": len(self.running_jobs),
            "queued_jobs": len(self.job_queue),
            "is_quiet_time": self.is_quiet_time(),
            "running_job_ids": list(self.running_jobs.keys()),
            "queued_job_ids": self.job_queue.copy(),
        }

    async def run_scheduler(self):
        """Main scheduler loop - runs indefinitely."""
        while True:
            # Process queued jobs if there's capacity
            await self._process_queue()

            # Wait before checking again
            await asyncio.sleep(1)
