"""Job queue and management for XSArena."""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Job:
    """A job in the queue."""

    id: str
    name: str
    func: Callable
    args: List[Any]
    kwargs: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    result: Any = None
    error: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class JobQueue:
    """Manages a queue of long-running jobs."""

    def __init__(self, state_file: str = ".xsarena/job_state.json"):
        self.jobs: List[Job] = []
        self.state_file = state_file
        self._load_state()

    def add_job(self, name: str, func: Callable, *args, **kwargs) -> str:
        """Add a job to the queue and return its ID."""
        job_id = f"job_{len(self.jobs)}_{int(datetime.now().timestamp())}"
        job = Job(id=job_id, name=name, func=func, args=list(args), kwargs=kwargs)
        self.jobs.append(job)
        self._save_state()
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    async def run_next(self) -> bool:
        """Run the next pending job. Returns True if there was a job to run."""
        for job in self.jobs:
            if job.status == "pending":
                return await self._execute_job(job)
        return False

    async def _execute_job(self, job: Job) -> bool:
        """Execute a single job."""
        job.status = "running"
        job.started_at = datetime.now()
        self._save_state()

        try:
            # Execute the job function
            if asyncio.iscoroutinefunction(job.func):
                result = await job.func(*job.args, **job.kwargs)
            else:
                result = job.func(*job.args, **job.kwargs)

            job.result = result
            job.status = "completed"
            job.completed_at = datetime.now()
        except Exception as e:
            job.error = str(e)
            job.status = "failed"
            job.completed_at = datetime.now()

        self._save_state()
        return True

    async def run_all(self):
        """Run all pending jobs sequentially."""
        while await self.run_next():
            pass  # Continue until no more jobs

    def _save_state(self):
        """Save the current state to a file."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        state_data = []
        for job in self.jobs:
            job_dict = {
                "id": job.id,
                "name": job.name,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
                "result": (
                    str(job.result) if job.result else None
                ),  # Store as string to avoid serialization issues
                "error": job.error,
            }
            state_data.append(job_dict)

        with open(self.state_file, "w") as f:
            json.dump(state_data, f, indent=2)

    def _load_state(self):
        """Load the state from a file."""
        if not os.path.exists(self.state_file):
            return

        with open(self.state_file, "r") as f:
            state_data = json.load(f)

        for job_data in state_data:
            job = Job(
                id=job_data["id"],
                name=job_data["name"],
                func=lambda: None,  # Placeholder, actual function will be different each time
                args=[],
                kwargs={},
            )
            job.status = job_data["status"]
            if job_data["created_at"]:
                job.created_at = datetime.fromisoformat(job_data["created_at"])
            if job_data["started_at"]:
                job.started_at = datetime.fromisoformat(job_data["started_at"])
            if job_data["completed_at"]:
                job.completed_at = datetime.fromisoformat(job_data["completed_at"])
            job.result = job_data["result"]
            job.error = job_data["error"]

            self.jobs.append(job)


class WatchMode:
    """Watches a directory for file changes and processes them."""

    def __init__(self, directory: str, process_func: Callable):
        self.directory = directory
        self.process_func = process_func
        self.running = False

    async def start(self):
        """Start watching the directory."""
        try:
            import asyncio

            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            print("watchdog not available, install with 'pip install watchdog'")
            return

        class FileChangeHandler(FileSystemEventHandler):
            def __init__(self, process_func):
                self.process_func = process_func

            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith((".txt", ".md")):
                    # Create a new event loop for the task if needed
                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    asyncio.create_task(self.process_file(event.src_path))

            def on_created(self, event):
                if not event.is_directory and event.src_path.endswith((".txt", ".md")):
                    # Create a new event loop for the task if needed
                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    asyncio.create_task(self.process_file(event.src_path))

            async def process_file(self, filepath):
                await self.process_func(filepath)

        self.running = True
        event_handler = FileChangeHandler(self.process_func)
        observer = Observer()
        observer.schedule(event_handler, self.directory, recursive=True)
        observer.start()

        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        finally:
            observer.join()

    def stop(self):
        """Stop watching the directory."""
        self.running = False
