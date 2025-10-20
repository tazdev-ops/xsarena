"""Job manager facade for XSArena v0.3."""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from pydantic import BaseModel

from ..backends.transport import BackendTransport, BaseEvent
from ..v2_orchestrator.specs import RunSpecV2

# Needed for exception mapping in map_exception_to_error_code
try:
    import aiohttp  # type: ignore
except Exception:  # pragma: no cover
    aiohttp = None  # type: ignore
try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore


def map_exception_to_error_code(exception: Exception) -> str:
    """Map common exceptions to standardized error codes."""
    error_map = {
        # Configuration errors
        KeyError: "invalid_config",  # When config keys are missing
        ValueError: "invalid_config",  # When config values are invalid
        FileNotFoundError: "file_not_found",
        # Content/Processing errors
        UnicodeDecodeError: "encoding_error",
        json.JSONDecodeError: "json_error",
    }

    # Add aiohttp-specific mappings only if aiohttp is available
    if aiohttp is not None:
        error_map.update(
            {
                aiohttp.ClientError: "transport_unavailable",
                aiohttp.ClientConnectorError: "transport_unavailable",
                aiohttp.ServerTimeoutError: "transport_timeout",
                aiohttp.ClientResponseError: "api_error",
            }
        )

    # Add requests-specific mappings only if requests is available
    if requests is not None:
        error_map.update(
            {
                requests.ConnectionError: "transport_unavailable",
                requests.Timeout: "transport_timeout",
            }
        )

    # Always include the base ConnectionError
    error_map[ConnectionError] = "transport_unavailable"

    # Check if it's a specific HTTP error with status code
    if hasattr(exception, "status") and isinstance(exception.status, int):
        status_code = exception.status
        if status_code == 401 or status_code == 403:
            return "auth_error"
        elif status_code == 429:
            return "quota_exceeded"
        elif status_code >= 500:
            return "server_error"
        elif status_code >= 400:
            return "api_error"

    # Try to match exact exception type
    for exc_type, error_code in error_map.items():
        if isinstance(exception, exc_type):
            return error_code

    # Check by name if exact type doesn't match
    exc_name = type(exception).__name__
    if "auth" in exc_name.lower() or "Auth" in exc_name:
        return "auth_error"
    elif (
        "quota" in exc_name.lower()
        or "Quota" in exc_name
        or "limit" in exc_name.lower()
    ):
        return "quota_exceeded"
    elif "connection" in exc_name.lower() or "Connection" in exc_name:
        return "transport_unavailable"
    elif "timeout" in exc_name.lower() or "Timeout" in exc_name:
        return "transport_timeout"

    # Default error code
    return "unknown_error"


def get_user_friendly_error_message(error_code: str) -> str:
    """Get user-friendly error message for an error code."""
    messages = {
        "transport_unavailable": "Transport unavailable - check network connection or backend status",
        "transport_timeout": "Request timed out - backend may be slow to respond",
        "auth_error": "Authentication failed - check API key or credentials",
        "quota_exceeded": "Quota exceeded - rate limit reached or account limit exceeded",
        "api_error": "API error - backend returned an error response",
        "server_error": "Server error - backend temporarily unavailable",
        "invalid_config": "Invalid configuration - check your settings",
        "file_not_found": "File not found - check the file path",
        "encoding_error": "Encoding error - file contains invalid characters",
        "json_error": "JSON parsing error - check file format",
        "unknown_error": "An unknown error occurred",
    }
    return messages.get(error_code, "An error occurred")


class JobV3(BaseModel):
    """Version 3 job model with typed fields."""

    id: str
    name: str
    run_spec: RunSpecV2
    backend: str
    state: str = "PENDING"  # PENDING/RUNNING/STALLED/RETRYING/DONE/FAILED/CANCELLED
    retries: int = 0
    created_at: str = datetime.now().isoformat()
    updated_at: str = datetime.now().isoformat()
    artifacts: Dict[str, str] = {}
    meta: Dict[str, Any] = {}
    progress: Dict[str, Any] = {}  # Track progress like chunks completed, tokens used


from .executor import JobExecutor
from .store import JobStore


class JobManager:
    """Version 3 job manager facade with typed events and async event bus."""

    def __init__(self, project_defaults: Optional[Dict[str, Any]] = None):
        self.defaults = project_defaults or {}
        self.job_store = JobStore()
        self.executor = JobExecutor(self.job_store)
        self.event_handlers: List[Callable[[BaseEvent], Awaitable[None]]] = []
        # Add control_queues attribute for compatibility with tests
        self.control_queues = self.executor.control_queues

    def register_event_handler(self, handler: Callable[[BaseEvent], Awaitable[None]]):
        """Register an event handler for job events."""
        self.event_handlers.append(handler)

    async def _emit_event(self, event: BaseEvent):
        """Emit an event to all registered handlers."""
        for handler in self.event_handlers:
            try:
                await handler(event)
            except Exception:
                # Log error but don't fail the job due to event handler issues
                pass

    def submit(
        self,
        run_spec: "RunSpecV2",
        backend: str = "bridge",
        system_text: str = "",
        session_state: Optional["SessionState"] = None,
    ) -> str:
        """Submit a new job with the given run specification. If a job with same output file exists and is incomplete, resume from last completed chunk."""
        # Check if a job with the same output file already exists
        out_path = (
            run_spec.out_path
            or f"./books/{run_spec.subject.replace(' ', '_')}.final.md"
        )

        # Look for existing jobs with the same output file
        existing_job_id = None
        for job in self.list_jobs():
            if job.run_spec.out_path == out_path or (
                not job.run_spec.out_path
                and out_path.endswith(
                    job.run_spec.subject.replace(" ", "_") + ".final.md"
                )
            ):
                # Check if the job is incomplete (not in DONE, FAILED, or CANCELLED state)
                if job.state not in ["DONE", "FAILED", "CANCELLED"]:
                    existing_job_id = job.id
                    break

        if existing_job_id:
            # Resume the existing job
            last_chunk = self.job_store._get_last_completed_chunk(existing_job_id)

            # Update job state to PENDING to restart processing
            job = self.load(existing_job_id)
            job.state = "PENDING"
            job.updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            self.job_store.save(job)

            # Log resume event
            resume_event = {
                "type": "job_resumed_from_chunk",
                "last_completed_chunk": last_chunk,
                "resuming_from_chunk": last_chunk + 1,
            }
            self.job_store._log_event(existing_job_id, resume_event)

            return existing_job_id
        else:
            # Create a new job as before
            job_id = str(uuid.uuid4())
            job = JobV3(
                id=job_id,
                name=run_spec.subject,
                run_spec=run_spec,
                backend=backend,
                state="PENDING",
                meta=(
                    {
                        "system_text": system_text,
                        "session_state": (
                            session_state.to_dict() if session_state else {}
                        ),
                    }
                    if system_text or session_state
                    else {
                        "session_state": (
                            session_state.to_dict() if session_state else {}
                        )
                    }
                ),
            )
            jd = self.job_store._job_dir(job_id)
            jd.mkdir(parents=True, exist_ok=True)

            # Save job metadata
            self.job_store.save(job)

            # Initialize events log
            event_data = {
                "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "type": "job_submitted",
                "job_id": job_id,
                "spec": run_spec.model_dump(),
            }
            self.job_store._log_event(job_id, event_data)

            return job_id

    def load(self, job_id: str) -> JobV3:
        """Load a job by ID."""
        return self.job_store.load(job_id)

    def _save_job(self, job: JobV3):
        """Save job metadata."""
        self.job_store.save(job)

    def _ts(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def list_jobs(self) -> List[JobV3]:
        """List all jobs."""
        return self.job_store.list_all()

    def _log_event(self, job_id: str, ev: Dict[str, Any]):
        """Log an event for a job with standardized structure."""
        self.job_store._log_event(job_id, ev)

    def submit_continue(
        self,
        run_spec: "RunSpecV2",
        file_path: str,
        until_end: bool = False,
        system_text: str = "",
        session_state: Optional["SessionState"] = None,
    ) -> str:
        """Submit a continue job with the given run specification and file path."""
        job_id = str(uuid.uuid4())
        job = JobV3(
            id=job_id,
            name=f"Continue: {run_spec.subject}",
            run_spec=run_spec,
            backend=run_spec.backend or "bridge",
            state="PENDING",
            meta=(
                {
                    "continue_from_file": file_path,
                    "until_end": until_end,
                    "system_text": system_text,
                    "session_state": session_state.to_dict() if session_state else {},
                }
                if system_text or session_state
                else {
                    "continue_from_file": file_path,
                    "until_end": until_end,
                    "session_state": session_state.to_dict() if session_state else {},
                }
            ),
        )
        jd = self.job_store._job_dir(job_id)
        jd.mkdir(parents=True, exist_ok=True)

        # Save job metadata
        self.job_store.save(job)

        # Initialize events log
        event_data = {
            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "type": "job_submitted",
            "job_id": job_id,
            "spec": run_spec.model_dump(),
            "continue_from_file": file_path,
            "until_end": until_end,
        }
        self.job_store._log_event(job_id, event_data)

        return job_id

    def _normalize_out(self, run_spec) -> str:
        """Mirror how run spec/out_path is constructed in orchestrator/run."""
        base = (
            run_spec.out_path
            or f"./books/{run_spec.subject.replace(' ', '_')}.final.md"
        )
        return os.path.abspath(base)

    def find_resumable_job_by_output(self, out_path: str) -> Optional[str]:
        """Find an existing job (not DONE/FAILED/CANCELLED) that targets out_path."""
        return self.job_store.find_resumable(out_path)

    def prepare_job_for_resume(self, job_id: str) -> str:
        """Set job to PENDING and log; used to requeue a non-running job."""
        job = self.load(job_id)
        job.state = "PENDING"
        job.updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self._save_job(job)
        self._log_event(job_id, {"type": "job_prepared_for_resume"})
        return job_id

    async def run_job(
        self,
        job_id: str,
        transport: BackendTransport,
        control_queue: asyncio.Queue = None,
        resume_event: asyncio.Event = None,
    ):
        """Run a job by delegating its execution to the JobExecutor."""
        job = self.load(job_id)

        # The executor requires an on_event callback. We'll define a simple one
        # here that emits events to any registered handlers.
        async def on_event_handler(event: BaseEvent):
            await self._emit_event(event)

        # Use the executor's control queues and resume events to ensure consistency
        # Use provided control queue and resume event if available, otherwise create new ones
        if control_queue is not None:
            self.executor.control_queues[job_id] = control_queue
        elif job_id not in self.executor.control_queues:
            self.executor.control_queues[job_id] = asyncio.Queue()

        if resume_event is not None:
            self.executor.resume_events[job_id] = resume_event
        elif job_id not in self.executor.resume_events:
            self.executor.resume_events[job_id] = asyncio.Event()
            self.executor.resume_events[job_id].set()  # Initially not paused

        # Delegate the entire run loop to the executor.
        await self.executor.run(
            job=job,
            transport=transport,
            on_event=on_event_handler,
            control_queue=self.executor.control_queues[job_id],
            resume_event=self.executor.resume_events[job_id],
        )

    async def send_control_message(self, job_id: str, command: str, text: str = None):
        """Send a control message to a running job."""
        # Use the executor's control queues
        if job_id not in self.executor.control_queues:
            self.executor.control_queues[job_id] = asyncio.Queue()

        message = {"type": command}
        if text:
            message["text"] = text

        await self.executor.control_queues[job_id].put(message)

        # Log the control command
        self._log_event(
            job_id, {"type": f"control_{command}", "command": command, "text": text}
        )

    async def wait_for_job_completion(self, job_id: str):
        """Wait for a job to reach a terminal state (DONE/FAILED/CANCELLED)."""

        while True:
            job = self.load(job_id)
            if job.state in ["DONE", "FAILED", "CANCELLED"]:
                break
            # Check every 2 seconds
            await asyncio.sleep(2.0)

        # Print final status
        if job.state == "DONE":
            print("[run] Job completed successfully")
        elif job.state == "FAILED":
            # Try to get more detailed error information from events
            error_message = self._get_last_error_message(job_id)
            if error_message:
                print(f"[run] Job failed: {error_message}")
            else:
                print("[run] Job failed")
        elif job.state == "CANCELLED":
            print("[run] Job cancelled")

    def _get_last_error_message(self, job_id: str) -> str:
        """Get the last error message from job events."""
        import json

        events_file = self.job_store._events_path(job_id)
        if not events_file.exists():
            return ""

        # Read the last few lines of the events file to find error events
        try:
            with open(events_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Look at the last 10 lines to find error events
            for line in reversed(lines[-10:]):
                try:
                    event = json.loads(line.strip())
                    if event.get("type") == "error" and "user_message" in event:
                        return event["user_message"]
                    elif event.get("type") == "error" and "message" in event:
                        return event["message"]
                    elif event.get("type") == "job_failed" and "error" in event:
                        return str(event["error"])
                except (json.JSONDecodeError, KeyError):
                    continue

            # If no specific error message found, check for any error-related events
            for line in reversed(lines[-20:]):  # Check more lines if needed
                try:
                    event = json.loads(line.strip())
                    if "error" in event or event.get("type") == "error":
                        message = event.get(
                            "user_message", event.get("message", event.get("error", ""))
                        )
                        if message:
                            return str(message)
                except (json.JSONDecodeError, KeyError):
                    continue

        except Exception:
            # If there's an issue reading the events file, return empty string
            pass

        return ""
