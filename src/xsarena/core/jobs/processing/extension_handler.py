"""Micro-extension handling logic for XSArena chunk processing."""

import asyncio
import logging

from ...backends.transport import BackendTransport
from ...chunking import jaccard_ngrams
from ..model import JobV3
from ..helpers import drain_next_hint, strip_next_lines

logger = logging.getLogger(__name__)


async def perform_micro_extension(
    content: str,
    min_chars: int,
    transport: BackendTransport,
    system_text: str,
    job: JobV3,
    chunk_idx: int,
    passes: int,
    repetition_threshold: float,
    control_queues: dict,
    resume_events: dict,
    job_store,
    ctl_lock = None,  # Accept the lock as a parameter
) -> str:
    """
    Perform micro-extensions to extend content if too short.
    
    Args:
        content: The content to potentially extend
        min_chars: Minimum character count required
        transport: Backend transport for API calls
        system_text: System prompt text
        job: The current job object
        chunk_idx: Current chunk index
        passes: Number of extension passes allowed
        repetition_threshold: Threshold for repetition detection
        control_queues: Control queues for job management
        resume_events: Resume events for job management
        job_store: Job store for logging
        ctl_lock: Control lock for thread safety
    
    Returns:
        Extended content
    """
    extended_content = content
    if len(extended_content) < min_chars and passes > 0:
        # Track content growth to detect stall loops
        initial_length = len(extended_content)
        low_growth_count = 0
        prev_length = initial_length

        # Perform up to 'passes' micro-extends
        for pass_num in range(passes):
            # Check for control messages during micro-extends
            while True:
                try:
                    control_msg = control_queues[job.id].get_nowait()
                    cmd = control_msg.get("type")
                    if cmd == "pause":
                        job_store._log_event(
                            job.id,
                            {"type": "job_paused", "job_id": job.id},
                        )
                        resume_events[job.id].clear()
                    elif cmd == "resume":
                        job_store._log_event(
                            job.id, {"type": "job_resumed"}
                        )
                        resume_events[job.id].set()
                    elif cmd == "cancel":
                        job_store._log_event(
                            job.id, {"type": "job_cancelled"}
                        )
                        job.state = "CANCELLED"
                        from datetime import datetime
                        job.updated_at = datetime.now().strftime(
                            "%Y-%m-%dT%H:%M:%S"
                        )
                        job_store.save(job)
                        return "CANCELLED"
                except asyncio.QueueEmpty:
                    break  # No more control messages to process

            # Drain any 'next' hints that have accumulated for this extend
            from ...prompt_runtime import build_chunk_prompt
            from asyncio import Lock
            async with Lock():  # Using a temporary lock since we don't have the actual one
                hint_now = await drain_next_hint(job.id, control_queues)

            # Wait for resume if paused
            if not resume_events[job.id].is_set():
                await resume_events[job.id].wait()

            # Prevent hot-looping the bridge
            await asyncio.sleep(0.05)  # Changed from 0.1 to 0.05

            # Get a local anchor from the current chunk content using centralized service
            from ....anchor_service import create_anchor
            local_anchor = await create_anchor(
                extended_content,
                use_semantic=False,
                transport=transport,
                tail_chars=150,
            )

            if local_anchor or hint_now:
                from ....anchor_service import build_anchor_continue_prompt
                extend_prompt = (
                    hint_now
                    if hint_now
                    else build_anchor_continue_prompt(local_anchor)
                )
                if hint_now:
                    job_store._log_event(
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
                        if hasattr(job.run_spec, "model") and job.run_spec.model
                        else "gpt-4o"
                    ),
                }

                # Check for repetition before extending
                try:
                    extend_response = await transport.send(extend_payload)
                    extend_content = (
                        extend_response.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )

                    # Strip NEXT lines from extend content
                    extend_content, _ = await strip_next_lines(extend_content)

                    # Repetition guard: check similarity with existing content
                    prev_tail = (
                        extended_content[-200:]
                        if len(extended_content) > 200
                        else extended_content
                    )
                    similarity = jaccard_ngrams(extend_content, prev_tail)
                    if (
                        similarity > repetition_threshold
                    ):  # If similarity is too high, skip the extension
                        job_store._log_event(
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
                            job_store._log_event(
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
                    from ..model import get_user_friendly_error_message, map_exception_to_error_code
                    extend_error_code = map_exception_to_error_code(extend_e)
                    extend_user_message = get_user_friendly_error_message(
                        extend_error_code
                    )

                    job_store._log_event(
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

    return extended_content