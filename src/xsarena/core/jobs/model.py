"""Job manager facade for XSArena v0.3."""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
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
        # Network/Transport errors
        aiohttp.ClientError: "transport_unavailable",
        aiohttp.ClientConnectorError: "transport_unavailable",
        aiohttp.ServerTimeoutError: "transport_timeout",
        requests.ConnectionError: "transport_unavailable",
        requests.Timeout: "transport_timeout",
        ConnectionError: "transport_unavailable",
        # API/Authentication errors
        aiohttp.ClientResponseError: "api_error",
        # Quota/Rate limit errors (often have specific status codes)
        # We'll check status codes in the exception handling
        # Configuration errors
        KeyError: "invalid_config",  # When config keys are missing
        ValueError: "invalid_config",  # When config values are invalid
        FileNotFoundError: "file_not_found",
        # Content/Processing errors
        UnicodeDecodeError: "encoding_error",
        json.JSONDecodeError: "json_error",
    }

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


import contextlib

from .executor import JobExecutor
from .store import JobStore


class JobManager:
    """Version 3 job manager facade with typed events and async event bus."""

    def __init__(self, project_defaults: Optional[Dict[str, Any]] = None):
        self.defaults = project_defaults or {}
        self.job_store = JobStore()
        self.executor = JobExecutor(self.job_store)
        self.event_handlers: List[Callable[[BaseEvent], Awaitable[None]]] = {}

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

    async def run_job(self, job_id: str, transport: BackendTransport):
        """Run a job with the given transport."""
        job = self.load(job_id)
        job.state = "RUNNING"
        job.updated_at = self._ts()
        self._save_job(job)

        # Emit job started event
        job_started_event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "job_id": job_id,
            "spec": job.run_spec.model_dump(),
        }
        await self._emit_event(BaseEvent(**job_started_event))
        self._log_event(job_id, {"type": "job_started"})

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
                    f.write(("\n\n" if not body.startswith("\n") else "") + body)
                # Add flush/fsync for durability
                f.flush()
                with contextlib.suppress(Exception):
                    os.fsync(f.fileno())

            # Log chunk completion
            self._log_event(
                job_id,
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
                "job_id": job_id,
                "chunk_id": f"chunk_{idx}",
                "result": body,
            }
            await self._emit_event(BaseEvent(**chunk_done_event))

        async def on_event(ev_type: str, payload: Dict[str, Any]):
            """Callback for other events."""
            self._log_event(job_id, {"type": ev_type, "job_id": job_id, **payload})

        async def _strip_next_lines(content: str) -> tuple[str, Optional[str]]:
            """Strip terminal NEXT directive variants and return hint."""
            patterns = [
                r"\s*NEXT\s*:\s*\[([^\]]+)\]\s*$",
                r"\s*Next\s*:\s*\[([^\]]+)\]\s*$",
                r"\s*next\s*:\s*\[([^\]]+)\]\s*$",
            ]
            hint = None
            for pat in patterns:
                m = re.search(pat, content, flags=re.IGNORECASE)
                if m:
                    if m.groups():
                        hint = m.group(1).strip()
                    content = re.sub(pat, "", content, count=1, flags=re.IGNORECASE)
                    break
            # Purge any mid-body NEXT hints safely
            content = re.sub(
                r"\n?\s*NEXT\s*:\s*\[[^\]]*\]\s*\n?", "\n", content, flags=re.IGNORECASE
            )
            return content.strip(), hint

        async def _drain_next_hint(jid: str) -> Optional[str]:
            """Drain queued 'next' hints and return the latest text if any; requeue other messages."""
            q = self.control_queues.get(jid)
            if not q:
                return None
            pending: List[dict] = []
            latest: Optional[str] = None
            while True:
                try:
                    msg = q.get_nowait()
                    if msg.get("type") == "next":
                        latest = msg.get("text") or latest
                    else:
                        pending.append(msg)
                except asyncio.QueueEmpty:
                    break
            for m in pending:
                await q.put(m)
            return latest

        async def _do_run():
            """Internal function to perform the actual run."""
            from pathlib import Path

            from ..anchor_service import (
                build_anchor_continue_prompt,
                create_anchor,
            )
            from ..chunking import jaccard_ngrams

            # Create a control queue for this job if it doesn't exist
            if job_id not in self.control_queues:
                self.control_queues[job_id] = asyncio.Queue()

            # Create a resume event for this job if it doesn't exist
            if job_id not in self.resume_events:
                self.resume_events[job_id] = asyncio.Event()
                self.resume_events[job_id].set()  # Initially not paused

            # Get repetition threshold from job spec or session state, or use default
            repetition_threshold = 0.8  # default value

            # First check if session state has the value
            if "session_state" in job.meta and job.meta["session_state"]:
                from ..state import SessionState

                session_state = SessionState(**job.meta["session_state"])
                repetition_threshold = getattr(
                    session_state, "repetition_threshold", repetition_threshold
                )

            # Then check if run_spec has the value (job.run_spec doesn't have repetition_threshold directly)
            # But we can check if it's added to the run_spec in the future

            # Determine starting chunk index (resume from last completed + 1, or start from 1)
            start_chunk_idx = 1
            if job.state == "PENDING":  # If resuming, check for completed chunks
                last_completed = self._get_last_completed_chunk(job_id)
                if last_completed > 0:
                    start_chunk_idx = last_completed + 1
                    # Log that we're resuming from a specific chunk
                    self._log_event(
                        job_id,
                        {
                            "type": "resume_from_chunk",
                            "last_completed_chunk": last_completed,
                            "starting_chunk": start_chunk_idx,
                        },
                    )

            # This would integrate with the new autopilot FSM
            # For now, we'll simulate the process with anchored continuation and micro-extends
            for chunk_idx in range(start_chunk_idx, max_chunks + 1):
                # Check for control messages before processing this chunk
                while True:
                    try:
                        # Non-blocking check for control messages
                        control_msg = self.control_queues[job_id].get_nowait()
                        cmd = control_msg.get("type")
                        if cmd == "pause":
                            self._log_event(job_id, {"type": "job_paused"})
                            self.resume_events[
                                job_id
                            ].clear()  # Clear the event (paused)
                        elif cmd == "resume":
                            self._log_event(job_id, {"type": "job_resumed"})
                            self.resume_events[job_id].set()  # Set the event (resumed)
                        elif cmd == "cancel":
                            self._log_event(job_id, {"type": "job_cancelled"})
                            job.state = "CANCELLED"
                            job.updated_at = self._ts()
                            self._save_job(job)
                            return  # Exit the _do_run function early
                    except asyncio.QueueEmpty:
                        break  # No more control messages to process

                # Drain any 'next' hints that have accumulated and use the latest one
                next_hint = await _drain_next_hint(job_id)

                # Wait for resume if paused
                if not self.resume_events[job_id].is_set():
                    self._log_event(job_id, {"type": "waiting_for_resume"})
                    await self.resume_events[job_id].wait()

                # Use the system_text from job meta if available, otherwise use a default
                system_text = job.meta.get(
                    "system_text", f"Generate content for {job.run_spec.subject}"
                )

                # Apply outline-first toggle for the first chunk only if enabled
                outline_first_enabled = False
                if "session_state" in job.meta and job.meta["session_state"]:
                    from ..state import SessionState

                    session_state = SessionState(**job.meta["session_state"])
                    outline_first_enabled = getattr(
                        session_state, "outline_first_enabled", False
                    )

                if chunk_idx == 1 and outline_first_enabled:
                    outline_instruction = (
                        "\n\nOUTLINE-FIRST SCAFFOLD\n"
                        "- First chunk: produce a chapter-by-chapter outline consistent with the subject; end with NEXT: [Begin Chapter 1].\n"
                        "- Subsequent chunks: follow the outline; narrative prose; define terms once; no bullet walls."
                    )
                    system_text += outline_instruction

                # Use the helper function to build the chunk prompt
                from ..prompt_runtime import build_chunk_prompt

                # Check if semantic anchor is enabled in session state
                semantic_anchor_enabled = False
                session_state = None
                if "session_state" in job.meta and job.meta["session_state"]:
                    from ..state import SessionState

                    session_state = SessionState(**job.meta["session_state"])
                    semantic_anchor_enabled = getattr(
                        session_state, "semantic_anchor_enabled", False
                    )

                # Prepare anchor for subsequent chunks
                anchor = None
                if chunk_idx > 1:  # Only need anchor for chunks after the first
                    out_path = (
                        job.run_spec.out_path
                        or f"./books/{job.run_spec.subject.replace(' ', '_')}.final.md"
                    )
                    if Path(out_path).exists():
                        try:
                            content = Path(out_path).read_text(encoding="utf-8")
                            anchor = await create_anchor(
                                content,
                                use_semantic=semantic_anchor_enabled,
                                transport=transport,
                            )
                        except Exception:
                            pass  # If we can't read the file, continue without anchor

                # Get next hint
                next_hint = await _drain_next_hint(job_id)
                if next_hint:
                    self._log_event(
                        job_id,
                        {
                            "type": "next_hint_applied",
                            "job_id": job_id,
                            "hint": next_hint,
                            "chunk_idx": chunk_idx,
                        },
                    )

                # Build the chunk prompt using the helper function
                user_content = build_chunk_prompt(
                    chunk_idx=chunk_idx,
                    job=job,
                    session_state=session_state,
                    next_hint=next_hint,
                    anchor=anchor,
                )

                payload = {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_text,
                        },
                        {
                            "role": "user",
                            "content": user_content,
                        },
                    ],
                    "model": (
                        job.run_spec.model
                        if hasattr(job.run_spec, "model") and job.run_spec.model
                        else "gpt-4o"
                    ),
                }

                try:
                    response = await transport.send(payload)
                    content = (
                        response.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )

                    # Strip NEXT: lines from content and extract hint
                    stripped_content, next_hint = await _strip_next_lines(content)

                    # Record the hint to events.jsonl
                    if next_hint:
                        self._log_event(
                            job_id,
                            {
                                "type": "next_hint",
                                "chunk_idx": chunk_idx,
                                "hint": next_hint,
                            },
                        )

                    # Get min_chars from the resolved spec, overridden by session state if available
                    resolved = job.run_spec.resolved()

                    # Override with session state values if available
                    if "session_state" in job.meta and job.meta["session_state"]:
                        from ..state import SessionState

                        session_state = SessionState(**job.meta["session_state"])
                        resolved["min_length"] = getattr(
                            session_state, "output_min_chars", resolved["min_length"]
                        )

                    min_chars = resolved["min_length"]

                    # Apply token-aware scaling if enabled in session state
                    if "session_state" in job.meta and job.meta["session_state"]:
                        from ..state import SessionState

                        session_state = SessionState(**job.meta["session_state"])
                        if getattr(session_state, "smart_min_enabled", False):
                            from ..utils.token_estimator import (
                                chars_to_tokens_approx,
                                tokens_to_chars_approx,
                            )

                            # Estimate current token count for the target
                            estimated_tokens = chars_to_tokens_approx(
                                min_chars, stripped_content
                            )
                            # Convert back to chars with a small buffer to avoid underestimation
                            # Apply ±20% guard rails as specified
                            token_scaled_min_chars = tokens_to_chars_approx(
                                estimated_tokens, stripped_content
                            )
                            # Apply guard rails: cap ±20% of configured min_chars
                            min_limit = int(min_chars * 0.8)  # 80% of original
                            max_limit = int(min_chars * 1.2)  # 120% of original
                            min_chars = max(
                                min_limit, min(max_limit, token_scaled_min_chars)
                            )

                    passes = resolved["passes"]

                    # Perform micro-extends if the content is too short
                    extended_content = stripped_content
                    if len(stripped_content) < min_chars and passes > 0:
                        # Track content growth to detect stall loops
                        initial_length = len(extended_content)
                        low_growth_count = 0
                        prev_length = initial_length

                        # Perform up to 'passes' micro-extends
                        for pass_num in range(passes):
                            # Check for control messages during micro-extends
                            while True:
                                try:
                                    control_msg = self.control_queues[
                                        job_id
                                    ].get_nowait()
                                    cmd = control_msg.get("type")
                                    if cmd == "pause":
                                        self._log_event(
                                            job_id,
                                            {"type": "job_paused", "job_id": job_id},
                                        )
                                        self.resume_events[job_id].clear()
                                    elif cmd == "resume":
                                        self._log_event(job_id, {"type": "job_resumed"})
                                        self.resume_events[job_id].set()
                                    elif cmd == "cancel":
                                        self._log_event(
                                            job_id, {"type": "job_cancelled"}
                                        )
                                        job.state = "CANCELLED"
                                        job.updated_at = self._ts()
                                        self._save_job(job)
                                        return
                                except asyncio.QueueEmpty:
                                    break  # No more control messages to process

                            # Drain any 'next' hints that have accumulated for this extend
                            await _drain_next_hint(job_id)

                            # Wait for resume if paused
                            if not self.resume_events[job_id].is_set():
                                await self.resume_events[job_id].wait()

                            # Prevent hot-looping the bridge
                            await asyncio.sleep(0.1)

                            # Get a local anchor from the current chunk content using centralized service
                            # Since this is for micro-extends within a single chunk, we use simple text extraction
                            local_anchor = await create_anchor(
                                extended_content,
                                use_semantic=False,
                                transport=transport,
                                tail_chars=150,
                            )
                            hint_now = await _drain_next_hint(job_id)
                            if local_anchor or hint_now:
                                extend_prompt = (
                                    hint_now
                                    if hint_now
                                    else build_anchor_continue_prompt(local_anchor)
                                )
                                if hint_now:
                                    self._log_event(
                                        job_id,
                                        {
                                            "type": "next_hint_applied",
                                            "hint": hint_now,
                                            "chunk_idx": chunk_idx,
                                            "pass": pass_num,
                                        },
                                    )

                                extend_payload = {
                                    "messages": [
                                        {
                                            "role": "system",
                                            "content": system_text,
                                        },
                                        {
                                            "role": "user",
                                            "content": extend_prompt,
                                        },
                                    ],
                                    "model": (
                                        job.run_spec.model
                                        if hasattr(job.run_spec, "model")
                                        and job.run_spec.model
                                        else "gpt-4o"
                                    ),
                                }

                                # Check for repetition before extending
                                try:
                                    extend_response = await transport.send(
                                        extend_payload
                                    )
                                    extend_content = (
                                        extend_response.get("choices", [{}])[0]
                                        .get("message", {})
                                        .get("content", "")
                                    )

                                    # Strip NEXT lines from extend content
                                    extend_content, _ = await _strip_next_lines(
                                        extend_content
                                    )

                                    # Repetition guard: check similarity with existing content
                                    prev_tail = (
                                        extended_content[-200:]
                                        if len(extended_content) > 200
                                        else extended_content
                                    )
                                    similarity = jaccard_ngrams(
                                        extend_content, prev_tail
                                    )
                                    if (
                                        similarity > repetition_threshold
                                    ):  # If similarity is too high, skip the extension
                                        self._log_event(
                                            job_id,
                                            {
                                                "type": "repetition_guard",
                                                "chunk_idx": chunk_idx,
                                                "similarity": similarity,
                                                "action": "skipped_extend",
                                            },
                                        )
                                        break

                                    # Add the extension to the content
                                    extended_content += extend_content

                                    # Content-size guardrails: Check for low growth
                                    current_length = len(extended_content)
                                    growth = current_length - prev_length
                                    # Trim whitespace from extend_content before measuring length to avoid false positives
                                    trimmed_extend_content = extend_content.strip()
                                    min_expected_growth = max(
                                        50, len(trimmed_extend_content) * 0.1
                                    )  # At least 10% of added content or 50 chars

                                    if growth < min_expected_growth:
                                        low_growth_count += 1
                                        if (
                                            low_growth_count >= 2
                                        ):  # Stop if low growth happens twice in a row
                                            self._log_event(
                                                job_id,
                                                {
                                                    "type": "extend_abandoned_for_low_growth",
                                                    "chunk_idx": chunk_idx,
                                                    "pass": pass_num,
                                                    "current_length": current_length,
                                                    "growth": growth,
                                                    "min_expected_growth": min_expected_growth,
                                                    "low_growth_count": low_growth_count,
                                                },
                                            )
                                            break
                                    else:
                                        low_growth_count = (
                                            0  # Reset counter when growth is good
                                        )

                                    prev_length = current_length

                                    # If we've reached the minimum length, stop extending
                                    if len(extended_content) >= min_chars:
                                        break

                                except Exception as extend_e:
                                    extend_error_code = map_exception_to_error_code(
                                        extend_e
                                    )
                                    extend_user_message = (
                                        get_user_friendly_error_message(
                                            extend_error_code
                                        )
                                    )

                                    self._log_event(
                                        job_id,
                                        {
                                            "type": "extend_failed",
                                            "chunk_idx": chunk_idx,
                                            "attempt": pass_num,
                                            "error": str(extend_e),
                                            "error_code": extend_error_code,
                                            "user_message": extend_user_message,
                                        },
                                    )
                                    break

                    await on_chunk(chunk_idx, extended_content, next_hint)
                except Exception as e:
                    # Map exception to error code
                    error_code = map_exception_to_error_code(e)
                    user_message = get_user_friendly_error_message(error_code)

                    # Emit chunk failed event
                    chunk_failed_event = {
                        "event_id": str(uuid.uuid4()),
                        "timestamp": time.time(),
                        "job_id": job_id,
                        "chunk_id": f"chunk_{chunk_idx}",
                        "error_message": str(e),
                        "error_code": error_code,
                        "user_message": user_message,
                    }
                    await self._emit_event(BaseEvent(**chunk_failed_event))

                    # Log detailed error context
                    self._log_event(
                        job_id,
                        {
                            "type": "send_error_context",
                            "chunk_idx": chunk_idx,
                            "error_code": error_code,
                            "user_message": user_message,
                            "original_error": str(e),
                        },
                    )
                    raise

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
                    "job_id": job_id,
                    "result_path": out_path,
                    "total_chunks": max_chunks,
                }
                await self._emit_event(BaseEvent(**job_completed_event))

                self._log_event(
                    job_id,
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

                self._log_event(
                    job_id,
                    {
                        "type": "watchdog_timeout",
                        "timeout_seconds": watchdog_secs,
                    },
                )

                # Classify non-retriable errors
                non_retriable_set = {"auth_error", "invalid_config", "quota_exceeded"}
                is_retriable = error_code not in non_retriable_set

                # Log the retry decision to events.jsonl
                self._log_event(
                    job_id,
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
                    self._log_event(job_id, {"type": "retry", "attempt": attempt})
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                else:
                    job.state = "FAILED"
                    job_failed_event = {
                        "event_id": str(uuid.uuid4()),
                        "timestamp": time.time(),
                        "job_id": job_id,
                        "error_message": "watchdog timeout",
                        "error_code": error_code,
                        "user_message": user_message,
                    }
                    await self._emit_event(BaseEvent(**job_failed_event))

                    self._log_event(
                        job_id,
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
                self._log_event(
                    job_id,
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
                    self._log_event(
                        job_id,
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
                        "job_id": job_id,
                        "error_message": str(ex),
                        "error_code": error_code,
                        "user_message": user_message,
                    }
                    await self._emit_event(BaseEvent(**job_failed_event))

                    self._log_event(
                        job_id,
                        {
                            "type": "job_failed",
                            "error": str(ex),
                            "error_code": error_code,
                            "user_message": user_message,
                        },
                    )
                    break
            finally:
                job.updated_at = self._ts()
                self._save_job(job)

        self._log_event(job_id, {"type": "job_ended", "state": job.state})

        # Clean up resources after job ends
        if job_id in self.control_queues:
            del self.control_queues[job_id]
        if job_id in self.resume_events:
            del self.resume_events[job_id]

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
            print("[run] Job failed")
        elif job.state == "CANCELLED":
            print("[run] Job cancelled")
