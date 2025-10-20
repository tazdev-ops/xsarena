"""Chunk processing logic for XSArena v0.3."""

import asyncio
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional

from ...utils.token_estimator import chars_to_tokens_approx, tokens_to_chars_approx
from ..anchor_service import create_anchor
from ..backends.transport import BackendTransport, BaseEvent
from ..prompt_runtime import build_chunk_prompt
from .helpers import drain_next_hint, strip_next_lines
from .model import JobV3, get_user_friendly_error_message, map_exception_to_error_code

# Import from new modules
from .processing.extension_handler import perform_micro_extension
from .processing.metrics_tracker import apply_lossless_metrics_and_compression
from .store import JobStore


class ChunkProcessor:
    """Process individual chunks."""

    def __init__(
        self,
        job_store: JobStore,
        control_queues: Dict[str, asyncio.Queue],
        resume_events: Dict[str, asyncio.Event],
        ctl_lock: asyncio.Lock,
    ):
        self.job_store = job_store
        self.control_queues = control_queues
        self.resume_events = resume_events
        self._ctl_lock = ctl_lock

    async def process_chunk(
        self,
        chunk_idx: int,
        job: JobV3,
        transport: BackendTransport,
        on_event: Callable[[BaseEvent], Awaitable[None]],
        resolved: Dict,
        repetition_threshold: float,
        session_state: Optional["SessionState"] = None,
        max_chunks: int = 1,
        watchdog_secs: int = 300,
        max_retries: int = 3,
    ):
        """Process a single chunk with the given transport and callbacks."""

        # Check for control messages before processing this chunk
        while True:
            try:
                # Non-blocking check for control messages
                control_msg = self.control_queues[job.id].get_nowait()
                cmd = control_msg.get("type")
                if cmd == "pause":
                    self.job_store._log_event(job.id, {"type": "job_paused"})
                    self.resume_events[job.id].clear()  # Clear the event (paused)
                elif cmd == "resume":
                    self.job_store._log_event(job.id, {"type": "job_resumed"})
                    self.resume_events[job.id].set()  # Set the event (resumed)
                elif cmd == "cancel":
                    self.job_store._log_event(job.id, {"type": "job_cancelled"})
                    job.state = "CANCELLED"
                    job.updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    self.job_store.save(job)
                    return "CANCELLED"  # Return special status to indicate cancellation
            except asyncio.QueueEmpty:
                break  # No more control messages to process

        # Drain any 'next' hints that have accumulated and use the latest one
        async with self._ctl_lock:
            next_hint = await drain_next_hint(job.id, self.control_queues)

        # Wait for resume if paused
        if not self.resume_events[job.id].is_set():
            self.job_store._log_event(job.id, {"type": "waiting_for_resume"})
            await self.resume_events[job.id].wait()

        # Use the system_text from job meta if available, otherwise use a default
        system_text = job.meta.get(
            "system_text", f"Generate content for {job.run_spec.subject}"
        )

        # For chunk_idx > 1, get a local anchor from current file tail
        anchor = None
        if chunk_idx > 1:
            out_path = (
                job.run_spec.out_path
                or f"./books/{job.run_spec.subject.replace(' ', '_')}.final.md"
            )
            if Path(out_path).exists():
                try:
                    content = Path(out_path).read_text(encoding="utf-8")
                    use_semantic = session_state and getattr(
                        session_state, "semantic_anchor_enabled", False
                    )
                    anchor = await create_anchor(
                        content, use_semantic=use_semantic, transport=transport
                    )
                except Exception:
                    anchor = None

        if next_hint:
            self.job_store._log_event(
                job.id,
                {
                    "type": "next_hint_applied",
                    "job_id": job.id,
                    "hint": next_hint,
                    "chunk_idx": chunk_idx,
                },
            )

        # Build the chunk prompt using the helper function
        # Pass next_hint if present; only use anchor if next_hint is None
        hint_to_use = next_hint if next_hint is not None else anchor
        user_content = build_chunk_prompt(
            chunk_idx=chunk_idx,
            job=job,
            session_state=session_state,
            next_hint=hint_to_use,
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
                response.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

            # Strip NEXT: lines from content and extract hint
            stripped_content, next_hint = await strip_next_lines(content)

            # Record the hint to events.jsonl
            if next_hint:
                self.job_store._log_event(
                    job.id,
                    {
                        "type": "next_hint",
                        "chunk_idx": chunk_idx,
                        "hint": next_hint,
                    },
                )

            # Get min_chars from the resolved spec, overridden by session state if available
            min_chars = resolved["min_length"]

            # Apply token-aware scaling if enabled in session state
            if session_state and getattr(session_state, "smart_min_enabled", False):
                # Estimate current token count for the target
                estimated_tokens = chars_to_tokens_approx(min_chars, stripped_content)
                # Convert back to chars with a small buffer to avoid underestimation
                # Apply ±20% guard rails as specified
                token_scaled_min_chars = tokens_to_chars_approx(
                    estimated_tokens, stripped_content
                )
                # Apply guard rails: cap ±20% of configured min_chars
                min_limit = int(min_chars * 0.8)  # 80% of original
                max_limit = int(min_chars * 1.2)  # 120% of original
                min_chars = max(min_limit, min(max_limit, token_scaled_min_chars))

            passes = resolved["passes"]

            # Perform micro-extends if the content is too short
            extended_content = await perform_micro_extension(
                content=stripped_content,
                min_chars=min_chars,
                transport=transport,
                system_text=system_text,
                job=job,
                chunk_idx=chunk_idx,
                passes=passes,
                repetition_threshold=repetition_threshold,
                control_queues=self.control_queues,
                resume_events=self.resume_events,
                job_store=self.job_store,
                ctl_lock=self._ctl_lock,
            )

            # Check if the extension was cancelled
            if extended_content == "CANCELLED":
                return "CANCELLED"

            # NEW: Lossless metrics + optional compress pass (gated by session_state)
            try:
                extended_content = await apply_lossless_metrics_and_compression(
                    content=extended_content,
                    job=job,
                    chunk_idx=chunk_idx,
                    job_store=self.job_store,
                    transport=transport,
                    session_state=session_state,
                )
            except Exception:
                # Metrics must never break the run
                pass

            return extended_content, next_hint

        except Exception as e:
            # Map exception to error code
            error_code = map_exception_to_error_code(e)
            user_message = get_user_friendly_error_message(error_code)

            # Emit chunk failed event
            chunk_failed_event = {
                "event_id": str(uuid.uuid4()),
                "timestamp": time.time(),
                "job_id": job.id,
                "chunk_id": f"chunk_{chunk_idx}",
                "error_message": str(e),
                "error_code": error_code,
                "user_message": user_message,
            }
            await on_event(BaseEvent(**chunk_failed_event))

            # Log detailed error context
            self.job_store._log_event(
                job.id,
                {
                    "type": "send_error_context",
                    "chunk_idx": chunk_idx,
                    "error_code": error_code,
                    "user_message": user_message,
                    "original_error": str(e),
                },
            )
            raise

    async def _extend_if_needed(
        self,
        content: str,
        min_chars: int,
        transport: BackendTransport,
        system_text: str,
        job: JobV3,
        chunk_idx: int,
        passes: int,
        repetition_threshold: float,
    ):
        """Micro-extension logic to extend content if too short."""
        # This is now handled by the external module
        extended_content = await perform_micro_extension(
            content=content,
            min_chars=min_chars,
            transport=transport,
            system_text=system_text,
            job=job,
            chunk_idx=chunk_idx,
            passes=passes,
            repetition_threshold=repetition_threshold,
            control_queues=self.control_queues,
            resume_events=self.resume_events,
            job_store=self.job_store,
            ctl_lock=self._ctl_lock,
        )
        return extended_content

    async def _build_user_prompt(
        self,
        chunk_idx: int,
        job: JobV3,
        session_state: Optional["SessionState"] = None,
        next_hint: str = None,
        anchor: str = None,
    ) -> str:
        """Build the user prompt for the chunk."""
        # Pass next_hint if present; only use anchor if next_hint is None
        hint_to_use = next_hint if next_hint is not None else anchor
        return build_chunk_prompt(
            chunk_idx=chunk_idx,
            job=job,
            session_state=session_state,
            next_hint=hint_to_use,
            anchor=anchor,
        )

    async def _apply_lossless_metrics(
        self, content: str, job: JobV3, chunk_idx: int, transport, session_state=None
    ) -> str:
        """Apply lossless metrics computation and optional compression pass."""
        return await apply_lossless_metrics_and_compression(
            content=content,
            job=job,
            chunk_idx=chunk_idx,
            job_store=self.job_store,
            transport=transport,
            session_state=session_state,
        )
