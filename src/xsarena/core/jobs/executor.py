"""Job execution layer for XSArena v0.3."""

import asyncio
import contextlib
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from ...utils.density import avg_sentence_len, filler_rate, lexical_density
from ..backends.transport import BackendTransport, BaseEvent
from .helpers import drain_next_hint, strip_next_lines
from .model import JobV3, get_user_friendly_error_message, map_exception_to_error_code
from .store import JobStore


class JobExecutor:
    """Encapsulates job execution logic (single-job run loop)."""

    def __init__(self, job_store: JobStore):
        self.job_store = job_store
        self.control_queues: Dict[str, asyncio.Queue] = {}
        self.resume_events: Dict[str, asyncio.Event] = {}
        self._ctl_lock = asyncio.Lock()

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
                r"\n?\s*NEXT\s*:\s*[^\]]*\]\s*\n?", "\n", content, flags=re.IGNORECASE
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
            from ..anchor_service import (
                build_anchor_continue_prompt,
                create_anchor,
            )
            from ..chunking import jaccard_ngrams

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
                # Check for control messages before processing this chunk
                while True:
                    try:
                        # Non-blocking check for control messages
                        control_msg = self.control_queues[job.id].get_nowait()
                        cmd = control_msg.get("type")
                        if cmd == "pause":
                            self.job_store._log_event(job.id, {"type": "job_paused"})
                            self.resume_events[
                                job.id
                            ].clear()  # Clear the event (paused)
                        elif cmd == "resume":
                            self.job_store._log_event(job.id, {"type": "job_resumed"})
                            self.resume_events[job.id].set()  # Set the event (resumed)
                        elif cmd == "cancel":
                            self.job_store._log_event(job.id, {"type": "job_cancelled"})
                            job.state = "CANCELLED"
                            job.updated_at = datetime.now().strftime(
                                "%Y-%m-%dT%H:%M:%S"
                            )
                            self.job_store.save(job)
                            return  # Exit the _do_run function early
                    except asyncio.QueueEmpty:
                        break  # No more control messages to process

                # Drain any 'next' hints that have accumulated and use the latest one
                async with self._ctl_lock:
                    next_hint = await _drain_next_hint(job.id)

                # Wait for resume if paused
                if not self.resume_events[job.id].is_set():
                    self.job_store._log_event(job.id, {"type": "waiting_for_resume"})
                    await self.resume_events[job.id].wait()

                # Use the system_text from job meta if available, otherwise use a default
                system_text = job.meta.get(
                    "system_text", f"Generate content for {job.run_spec.subject}"
                )

                # Get session state if available
                session_state = None
                if "session_state" in job.meta and job.meta["session_state"]:
                    from ..state import SessionState

                    session_state = SessionState(**job.meta["session_state"])

                # Always await hint drain and prefer hint over anchor
                async with self._ctl_lock:
                    next_hint = await drain_next_hint(job.id, self.control_queues)

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
                from ..prompt_runtime import build_chunk_prompt

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
                        response.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
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
                                        job.id
                                    ].get_nowait()
                                    cmd = control_msg.get("type")
                                    if cmd == "pause":
                                        self.job_store._log_event(
                                            job.id,
                                            {"type": "job_paused", "job_id": job.id},
                                        )
                                        self.resume_events[job.id].clear()
                                    elif cmd == "resume":
                                        self.job_store._log_event(
                                            job.id, {"type": "job_resumed"}
                                        )
                                        self.resume_events[job.id].set()
                                    elif cmd == "cancel":
                                        self.job_store._log_event(
                                            job.id, {"type": "job_cancelled"}
                                        )
                                        job.state = "CANCELLED"
                                        job.updated_at = datetime.now().strftime(
                                            "%Y-%m-%dT%H:%M:%S"
                                        )
                                        self.job_store.save(job)
                                        return
                                except asyncio.QueueEmpty:
                                    break  # No more control messages to process

                            # Drain any 'next' hints that have accumulated for this extend
                            async with self._ctl_lock:
                                hint_now = await drain_next_hint(
                                    job.id, self.control_queues
                                )

                            # Wait for resume if paused
                            if not self.resume_events[job.id].is_set():
                                await self.resume_events[job.id].wait()

                            # Prevent hot-looping the bridge
                            await asyncio.sleep(0.05)  # Changed from 0.1 to 0.05

                            # Get a local anchor from the current chunk content using centralized service
                            local_anchor = await create_anchor(
                                extended_content,
                                use_semantic=False,
                                transport=transport,
                                tail_chars=150,
                            )

                            if local_anchor or hint_now:
                                extend_prompt = (
                                    hint_now
                                    if hint_now
                                    else build_anchor_continue_prompt(local_anchor)
                                )
                                if hint_now:
                                    self.job_store._log_event(
                                        job.id,
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
                                    extend_content, _ = await strip_next_lines(
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
                                        self.job_store._log_event(
                                            job.id,
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
                                            self.job_store._log_event(
                                                job.id,
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

                                    self.job_store._log_event(
                                        job.id,
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

                    # NEW: Lossless metrics + optional compress pass (gated by session_state)
                    try:
                        # Reconstruct session_state if present
                        sstate = None
                        if "session_state" in job.meta and job.meta["session_state"]:
                            from ..state import SessionState

                            sstate = SessionState(**job.meta["session_state"])
                        # Compute metrics
                        ld = lexical_density(extended_content)
                        fr = filler_rate(extended_content)
                        asl = avg_sentence_len(extended_content)
                        self.job_store._log_event(
                            job.id,
                            {
                                "type": "density_metrics",
                                "chunk_idx": chunk_idx,
                                "lexical_density": round(ld, 4),
                                "filler_per_k": round(fr, 2),
                                "avg_sentence_len": round(asl, 2),
                            },
                        )

                        enforce = (
                            bool(getattr(sstate, "lossless_enforce", False))
                            if sstate
                            else False
                        )
                        target_density = (
                            float(getattr(sstate, "target_density", 0.55))
                            if sstate
                            else 0.55
                        )
                        max_adverbs_k = (
                            int(getattr(sstate, "max_adverbs_per_k", 15))
                            if sstate
                            else 15
                        )
                        max_sent_len = (
                            int(getattr(sstate, "max_sentence_len", 22))
                            if sstate
                            else 22
                        )

                        needs_compress = enforce and (
                            ld < target_density
                            or fr > max_adverbs_k
                            or asl > max_sent_len
                        )
                        if needs_compress:
                            compress_prompt = (
                                "Lossless compression pass: Rewrite the EXACT content below to higher density.\n"
                                "- Preserve every fact and entailment.\n"
                                "- Remove fillers/hedges; avoid generic transitions.\n"
                                "- Do not add or remove claims.\n"
                                "CONTENT:\n<<<CHUNK\n" + extended_content + "\nCHUNK>>>"
                            )
                            extend_payload = {
                                "messages": [
                                    {
                                        "role": "system",
                                        "content": "You are a precision editor enforcing a lossless compression contract.",
                                    },
                                    {"role": "user", "content": compress_prompt},
                                ],
                                "model": (
                                    job.run_spec.model
                                    if hasattr(job.run_spec, "model")
                                    and job.run_spec.model
                                    else "gpt-4o"
                                ),
                            }
                            try:
                                compress_resp = await transport.send(extend_payload)
                                new_content = (
                                    compress_resp.get("choices", [{}])[0]
                                    .get("message", {})
                                    .get("content", "")
                                )
                                if new_content and len(new_content.strip()) > 0:
                                    extended_content = new_content.strip()
                                    # Recompute metrics after compress
                                    ld2 = lexical_density(extended_content)
                                    fr2 = filler_rate(extended_content)
                                    asl2 = avg_sentence_len(extended_content)
                                    self.job_store._log_event(
                                        job.id,
                                        {
                                            "type": "compress_pass",
                                            "chunk_idx": chunk_idx,
                                            "before": {
                                                "ld": round(ld, 4),
                                                "fr": round(fr, 2),
                                                "asl": round(asl, 2),
                                            },
                                            "after": {
                                                "ld": round(ld2, 4),
                                                "fr": round(fr2, 2),
                                                "asl": round(asl2, 2),
                                            },
                                        },
                                    )
                            except Exception:
                                # If compress fails, proceed with extended_content as-is
                                self.job_store._log_event(
                                    job.id,
                                    {
                                        "type": "compress_pass_failed",
                                        "chunk_idx": chunk_idx,
                                    },
                                )
                    except Exception:
                        # Metrics must never break the run
                        pass

                    await on_chunk(chunk_idx, extended_content, next_hint)
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
