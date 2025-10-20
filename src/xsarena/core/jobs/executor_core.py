"""Job execution layer for XSArena v0.3."""

import asyncio
import contextlib
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional

from ..backends.transport import BackendTransport, BaseEvent
from .chunk_processor import ChunkProcessor
from .model import JobV3, get_user_friendly_error_message, map_exception_to_error_code
from .store import JobStore


class JobExecutor:
    """Encapsulates job execution logic (single-job run loop)."""

    def __init__(self, job_store: JobStore):
        self.job_store = job_store
        self.control_queues: Dict[str, asyncio.Queue] = {}
        self.resume_events: Dict[str, asyncio.Event] = {}
        self._ctl_lock = asyncio.Lock()
        self.chunk_processor = ChunkProcessor(
            self.job_store, self.control_queues, self.resume_events, self._ctl_lock
        )

    async def run(
        self,
        job: JobV3,
        transport: BackendTransport,
        on_event: Callable[[BaseEvent], Awaitable[None]],
        control_queue: asyncio.Queue,
        resume_event: asyncio.Event,
    ):
        """Execute a job with the given transport and callbacks."""
        # Update job state to RUNNING
        job.state = "RUNNING"
        job.updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.job_store.save(job)

        # Emit job started event
        job_started_event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "job_id": job.id,
            "spec": job.run_spec.model_dump(),
        }
        await on_event(BaseEvent(**job_started_event))
        self.job_store._log_event(job.id, {"type": "job_started"})

        # Prepare output path
        out_path = (
            job.run_spec.out_path
            or f"./books/{job.run_spec.subject.replace(' ', '_')}.final.md"
        )
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        # Extract run parameters from spec
        resolved = job.run_spec.resolved()

        # Override with session state values if available
        if "session_state" in job.meta and job.meta["session_state"]:
            from ..state import SessionState

            session_state = SessionState(**job.meta["session_state"])
            resolved["min_length"] = getattr(
                session_state, "output_min_chars", resolved["min_length"]
            )

        max_chunks = resolved["chunks"]
        watchdog_secs = getattr(job.run_spec, "timeout", 300)
        max_retries = 3  # TODO: Make configurable

        async def on_chunk(idx: int, body: str, hint: Optional[str] = None):
            """Callback for when a chunk is completed."""
            with open(out_path, "a", encoding="utf-8") as f:
                if f.tell() == 0 or idx == 1:
                    f.write(body)
                else:
                    f.write(("" if body.startswith("\n") else "\n\n") + body)
                # Add flush/fsync for durability
                f.flush()
                with contextlib.suppress(Exception):
                    os.fsync(f.fileno())

            # Log chunk completion
            self.job_store._log_event(
                job.id,
                {
                    "type": "chunk_done",
                    "chunk_idx": idx,
                    "bytes": len(body),
                    "hint": hint,
                },
            )

            # Emit chunk done event
            chunk_done_event = {
                "event_id": str(uuid.uuid4()),
                "timestamp": time.time(),
                "job_id": job.id,
                "chunk_id": f"chunk_{idx}",
                "result": body,
            }
            await on_event(BaseEvent(**chunk_done_event))

        async def _do_run():
            """Internal function to perform the actual run."""

            # Store the control queue and resume event for this job
            self.control_queues[job.id] = control_queue
            self.resume_events[job.id] = resume_event
            resume_event.set()  # Initially not paused

            # Get repetition threshold from job spec or session state, or use default
            repetition_threshold = 0.35  # default value (matches state.py)

            # First check if session state has the value
            if "session_state" in job.meta and job.meta["session_state"]:
                from ..state import SessionState

                session_state = SessionState(**job.meta["session_state"])
                repetition_threshold = getattr(
                    session_state, "repetition_threshold", repetition_threshold
                )

            # Determine starting chunk index (resume from last completed + 1, or start from 1)
            start_chunk_idx = 1
            if job.state == "PENDING":  # If resuming, check for completed chunks
                last_completed = self.job_store._get_last_completed_chunk(job.id)
                if last_completed > 0:
                    start_chunk_idx = last_completed + 1
                    # Log that we're resuming from a specific chunk
                    self.job_store._log_event(
                        job.id,
                        {
                            "type": "resume_from_chunk",
                            "last_completed_chunk": last_completed,
                            "starting_chunk": start_chunk_idx,
                        },
                    )

            # This would integrate with the new autopilot FSM
            # For now, we'll simulate the process with anchored continuation and micro-extends
            for chunk_idx in range(start_chunk_idx, max_chunks + 1):
                # Process the chunk using the chunk processor
                result = await self.chunk_processor.process_chunk(
                    chunk_idx=chunk_idx,
                    job=job,
                    transport=transport,
                    on_event=on_event,
                    resolved=resolved,
                    repetition_threshold=repetition_threshold,
                    session_state=self._get_session_state(job),
                    max_chunks=max_chunks,
                    watchdog_secs=watchdog_secs,
                    max_retries=max_retries,
                )

                # Check if job was cancelled
                if result == "CANCELLED":
                    return  # Exit the _do_run function early

                # Unpack the result
                extended_content, next_hint = result

                await on_chunk(chunk_idx, extended_content, next_hint)

        # Run with retry logic
        attempt = 0
        while True:
            try:
                await asyncio.wait_for(_do_run(), timeout=watchdog_secs)

                # Mark job as completed
                job.artifacts["final"] = out_path
                job.state = "DONE"

                # Emit job completed event
                job_completed_event = {
                    "event_id": str(uuid.uuid4()),
                    "timestamp": time.time(),
                    "job_id": job.id,
                    "result_path": out_path,
                    "total_chunks": max_chunks,
                }
                await on_event(BaseEvent(**job_completed_event))

                self.job_store._log_event(
                    job.id,
                    {
                        "type": "job_completed",
                        "final": out_path,
                        "total_chunks": max_chunks,
                    },
                )
                break
            except asyncio.TimeoutError:
                error_code = "transport_timeout"
                user_message = get_user_friendly_error_message(error_code)

                self.job_store._log_event(
                    job.id,
                    {
                        "type": "watchdog_timeout",
                        "timeout_seconds": watchdog_secs,
                    },
                )

                # Classify non-retriable errors
                non_retriable_set = {"auth_error", "invalid_config", "quota_exceeded"}
                is_retriable = error_code not in non_retriable_set

                # Log the retry decision to events.jsonl
                self.job_store._log_event(
                    job.id,
                    {
                        "type": "retry_decision",
                        "error_code": error_code,
                        "is_retriable": is_retriable,
                        "retry_planned": is_retriable and attempt < max_retries,
                        "attempt": attempt,
                        "max_retries": max_retries,
                    },
                )

                if is_retriable and attempt < max_retries:
                    attempt += 1
                    self.job_store._log_event(
                        job.id, {"type": "retry", "attempt": attempt}
                    )
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                else:
                    job.state = "FAILED"
                    job_failed_event = {
                        "event_id": str(uuid.uuid4()),
                        "timestamp": time.time(),
                        "job_id": job.id,
                        "error_message": "watchdog timeout",
                        "error_code": error_code,
                        "user_message": user_message,
                    }
                    await on_event(BaseEvent(**job_failed_event))

                    self.job_store._log_event(
                        job.id,
                        {
                            "type": "job_failed",
                            "error": "watchdog timeout",
                            "error_code": error_code,
                            "user_message": user_message,
                        },
                    )
                    break
            except Exception as ex:
                error_code = map_exception_to_error_code(ex)
                user_message = get_user_friendly_error_message(error_code)

                # Classify non-retriable errors
                non_retriable_set = {"auth_error", "invalid_config", "quota_exceeded"}
                is_retriable = error_code not in non_retriable_set

                # Log the retry decision to events.jsonl
                self.job_store._log_event(
                    job.id,
                    {
                        "type": "retry_decision",
                        "error_code": error_code,
                        "is_retriable": is_retriable,
                        "retry_planned": is_retriable and attempt < max_retries,
                        "attempt": attempt,
                        "max_retries": max_retries,
                    },
                )

                if is_retriable and attempt < max_retries:
                    attempt += 1
                    self.job_store._log_event(
                        job.id,
                        {
                            "type": "retry",
                            "attempt": attempt,
                            "error": str(ex),
                            "error_code": error_code,
                            "user_message": user_message,
                        },
                    )
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                else:
                    job.state = "FAILED"
                    job_failed_event = {
                        "event_id": str(uuid.uuid4()),
                        "timestamp": time.time(),
                        "job_id": job.id,
                        "error_message": str(ex),
                        "error_code": error_code,
                        "user_message": user_message,
                    }
                    await on_event(BaseEvent(**job_failed_event))

                    self.job_store._log_event(
                        job.id,
                        {
                            "type": "job_failed",
                            "error": str(ex),
                            "error_code": error_code,
                            "user_message": user_message,
                        },
                    )
                    break
            finally:
                job.updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                self.job_store.save(job)

        self.job_store._log_event(job.id, {"type": "job_ended", "state": job.state})

        # Clean up resources after job ends
        if job.id in self.control_queues:
            del self.control_queues[job.id]
        if job.id in self.resume_events:
            del self.resume_events[job.id]

    def _get_session_state(self, job: JobV3):
        """Helper to get session state from job metadata."""
        if "session_state" in job.meta and job.meta["session_state"]:
            from ..state import SessionState

            return SessionState(**job.meta["session_state"])
        return None
