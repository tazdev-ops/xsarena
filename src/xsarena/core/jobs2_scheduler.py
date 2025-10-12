from datetime import datetime
from typing import Any, Dict


class JobScheduler:
    def __init__(self, project_defaults: Dict[str, Any]):
        self.project_defaults = project_defaults
        self.scheduler_config = project_defaults.get(
            "scheduler",
            {
                "concurrency": {
                    "total": project_defaults.get("concurrency_total", 1),
                    "bridge": project_defaults.get("concurrency_bridge", 1),
                    "openrouter": project_defaults.get("concurrency_openrouter", 2),
                    "ollama": project_defaults.get("concurrency_ollama", 1),
                },
                "quiet_hours": {
                    "start": project_defaults.get("quiet_hours_start", "01:00"),
                    "end": project_defaults.get("quiet_hours_end", "06:00"),
                    "enabled": project_defaults.get("quiet_hours_enabled", False),
                },
            },
        )
        self.running_jobs = {}  # job_id -> start_time

    def _is_quiet_hours(self) -> bool:
        """Check if current time is in quiet hours."""
        if not self.scheduler_config["quiet_hours"]["enabled"]:
            return False

        current_time = datetime.now().time()
        start_str = self.scheduler_config["quiet_hours"]["start"]
        end_str = self.scheduler_config["quiet_hours"]["end"]

        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()

        # Handle overnight periods (e.g., 23:00 to 06:00)
        if start_time > end_time:  # Overnight case
            return current_time >= start_time or current_time <= end_time
        else:  # Same-day period
            return start_time <= current_time <= end_time

    def _count_running_by_backend(self, backend: str) -> int:
        """Count how many jobs of specific backend are currently running."""
        count = 0
        # This method would need access to job runner's list_jobs method
        # For now, we'll just count from the running_jobs dict
        # In a full implementation, this would check actual running jobs
        for job_id in self.running_jobs:
            # This would need to get the backend from the job object
            # For now, this is a simplified implementation
            pass
        return count

    def can_run_now(self, job_id: str, backend: str) -> bool:
        """Check if a job can run now based on concurrency limits and quiet hours."""
        # Check quiet hours
        if self._is_quiet_hours():
            return False

        # Check total concurrency limit
        total_concurrent = len(self.running_jobs)
        total_limit = self.scheduler_config["concurrency"].get("total", 1)
        if total_concurrent >= total_limit:
            return False

        # Check backend-specific limit
        backend_count = self._count_running_by_backend(backend)
        backend_limit = self.scheduler_config["concurrency"].get(backend, 1)
        if backend_count >= backend_limit:
            return False

        return True
