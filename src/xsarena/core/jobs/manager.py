"""Job manager for XSArena."""

import asyncio
import logging
from typing import Any, Dict
from uuid import uuid4

from .errors import get_user_friendly_error_message, map_exception_to_error_code
from .executor_core import JobExecutor
from .model import JobV3
from .store import JobStore

logger = logging.getLogger(__name__)

# Module-level mappings for control queues and resume events so different instances share them
CONTROL_QUEUES: Dict[str, asyncio.Queue] = {}
RESUME_EVENTS: Dict[str, asyncio.Event] = {}


class JobManager:
    """Orchestration manager for jobs."""

    def __init__(self):
        """Initialize the job manager."""
        self.store = JobStore()
        self.executor = JobExecutor(self.store)
        self.control_queues = CONTROL_QUEUES
        self.resume_events = RESUME_EVENTS

    def list_jobs(self):
        """Return self.store.list_all()"""
        return self.store.list_all()

    def load(self, job_id):
        """Return self.store.load(job_id)"""
        return self.store.load(job_id)

    def find_resumable_job_by_output(self, out_path):
        """delegate to self.store.find_resumable(out_path)"""
        return self.store.find_resumable(out_path)

    def prepare_job_for_resume(self, job_id):
        """load job, set state="PENDING", update updated_at, save; return job_id"""
        job = self.store.load(job_id)
        job.state = "PENDING"
        from datetime import datetime

        job.updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.store.save(job)
        return job_id

    def submit(
        self,
        run_spec: Any,
        backend: str = "bridge",
        system_text: str = "",
        session_state=None,
    ) -> str:
        """create JobV3 with:
        - id = uuid4().hex
        - name = run_spec.subject
        - run_spec = run_spec
        - backend = backend
        - meta = {"system_text": system_text, "session_state": session_state.to_dict() if session_state else None}
        - Save via store.save(job); return job.id"""
        job_id = uuid4().hex
        job = JobV3(
            id=job_id,
            name=run_spec.subject,
            run_spec=run_spec,
            backend=backend,
            meta={
                "system_text": system_text,
                "session_state": session_state.to_dict() if session_state else None,
            },
        )
        self.store.save(job)
        return job.id

    def submit_continue(
        self, run_spec, file_path, until_end, system_text, session_state
    ):
        """identical to submit but ensure run_spec.out_path = file_path; return job.id"""
        run_spec.out_path = file_path
        return self.submit(
            run_spec,
            backend="bridge",
            system_text=system_text,
            session_state=session_state,
        )

    async def run_job(self, job_id, transport, control_queue, resume_event):
        """Load job via store
        - Put CONTROL_QUEUES[job_id] = control_queue and RESUME_EVENTS[job_id] = resume_event before calling executor
        - Define async on_event(e): no-op (or log if you want)
        - await self.executor.run(job, transport, on_event, control_queue, resume_event)
        """
        job = self.store.load(job_id)

        # Store control queue and resume event in module-level mappings
        CONTROL_QUEUES[job_id] = control_queue
        RESUME_EVENTS[job_id] = resume_event

        async def on_event(e):
            # no-op (or log if you want)
            pass

        await self.executor.run(job, transport, on_event, control_queue, resume_event)

    async def send_control_message(self, job_id, command, payload=""):
        """ensure CONTROL_QUEUES[job_id] exists; await CONTROL_QUEUES[job_id].put({"type": command, "text": payload})"""
        if job_id not in CONTROL_QUEUES:
            CONTROL_QUEUES[job_id] = asyncio.Queue()
        await CONTROL_QUEUES[job_id].put({"type": command, "text": payload})

    async def pause_job(self, job_id):
        """small wrappers that await send_control_message(job_id, "pause")"""
        await self.send_control_message(job_id, "pause")

    async def resume_job(self, job_id):
        """small wrappers that await send_control_message(job_id, "resume")"""
        await self.send_control_message(job_id, "resume")

    async def cancel_job(self, job_id):
        """small wrappers that await send_control_message(job_id, "cancel")"""
        await self.send_control_message(job_id, "cancel")

    def handle_job_error(self, job_id: str, exception: Exception):
        """Handle errors that occur during job execution."""
        error_code = map_exception_to_error_code(exception)
        error_message = get_user_friendly_error_message(error_code)
        logger.error(f"Job {job_id} failed with error {error_code}: {error_message}")
