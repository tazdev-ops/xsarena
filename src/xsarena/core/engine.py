"""Core engine for XSArena - handles communication with backends and manages session state."""

import re
from typing import Callable, List, Optional

from .backends import Backend, Message
from .chunking import anti_repeat_filter, build_anchor_prompt, detect_repetition
from .state import SessionState
from .templates import REPETITION_PROMPTS


class Engine:
    """Main engine that handles communication with backends and manages session state."""

    def __init__(self, backend: Backend, state: SessionState):
        self.backend = backend
        self.state = state
        self.tools: Optional[List[Callable]] = None  # For coder mode
        self.redaction_filter: Optional[Callable[[str], str]] = None

    async def send_and_collect(
        self, user_prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        """Send a message and collect the response, handling continuation and repetition."""
        # Build the full message history
        messages = []

        # Add system prompt if provided
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))

        # Add history (respecting window size)
        history_start = max(0, len(self.state.history) - self.state.window_size)
        for msg in self.state.history[history_start:]:
            messages.append(Message(role=msg.role, content=msg.content))

        # Add the current user prompt
        messages.append(Message(role="user", content=user_prompt))

        # Add continuation context if in anchor mode - use unified format
        if self.state.continuation_mode == "anchor" and self.state.anchors:
            anchor_text = " ".join(self.state.anchors[-3:])  # Use last 3 anchors
            # Use the unified anchor format by calling build_anchor_continue_prompt
            anchor_prompt = await self.build_anchor_continue_prompt(anchor_text)
            if anchor_prompt:
                # Append to the last user message or add as a new assistant message
                if messages and messages[-1].role == "user":
                    messages[-1].content += "\n" + anchor_prompt
                else:
                    messages.append(Message(role="user", content=anchor_prompt))

        # Apply redaction filter if enabled
        if self.redaction_filter:
            for msg in messages:
                msg.content = self.redaction_filter(msg.content)

        # Send to backend
        response = await self.backend.send(messages)

        # Post-process the response
        processed_response = await self.postprocess_response(response)

        # Add to history
        self.state.add_message("user", user_prompt)
        self.state.add_message("assistant", processed_response)

        # Add to anchors if in anchor mode
        if self.state.continuation_mode == "anchor":
            self.state.add_anchor(processed_response)

        return processed_response

    async def postprocess_response(self, response: str) -> str:
        """Post-process the response to handle repetition, CF flags, etc."""
        # Check for repetition
        if self.state.history:
            # Simple check against the last response
            last_response = ""
            for msg in reversed(self.state.history):
                if msg.role == "assistant":
                    last_response = msg.content
                    break

            if detect_repetition(response, self.state.repetition_threshold):
                # Handle repetition - for now, just return the response, but in the future
                # we might want to implement a retry mechanism
                print("Repetition detected, considering retry...")

                # Optional: implement retry with stricter prompt
                if False:  # This could be enabled based on a setting
                    anchor_context = build_anchor_prompt(
                        last_response, self.state.anchor_length
                    )
                    retry_prompt = REPETITION_PROMPTS["retry"].format(
                        anchor_context=anchor_context
                    )

                    # This would involve sending a new request with the retry prompt
                    # For now, we'll just continue with postprocessing

        # Apply anti-repeat filter
        processed = anti_repeat_filter(
            response,
            [msg.content for msg in self.state.history if msg.role == "assistant"],
        )

        # Strip NEXT tokens or other markers
        processed = re.sub(r"\[\[NEXT\]\]", "", processed)
        processed = processed.strip()

        return processed

    def set_tools(self, tools: List[Callable]):
        """Set tools for the engine (for coder mode)."""
        self.tools = tools

    def set_redaction_filter(self, filter_func: Callable[[str], str]):
        """Set a redaction filter to strip sensitive information."""
        self.redaction_filter = filter_func

    async def run_with_tools(self, user_prompt: str) -> str:
        """Run a prompt with tool support (for coder mode)."""
        if not self.tools:
            return await self.send_and_collect(user_prompt)

        # For now, this is a simplified implementation
        # In a full implementation, this would handle JSON tool calls
        return await self.send_and_collect(user_prompt)

    async def strip_next_marker(self, text: str):
        """Strip NEXT marker from text and return the body and hint separately."""
        import re

        hint = None
        last = None
        for m in re.finditer(r"^\s*NEXT:\s*(.+)\s*$", text, re.MULTILINE):
            last = m
        if last:
            hint = last.group(1).strip()
            text = text[: last.start()] + text[last.end() :]
        return text.rstrip(), hint

    async def build_anchor_continue_prompt(self, anchor: str) -> str:
        """Build an anchor continuation prompt."""
        # A compact, subject-free continuation instruction - unified format
        return (
            "Continue exactly from after the anchor; do not repeat or reintroduce; no summary.\n"
            "ANCHOR:\n<<<ANCHOR\n" + anchor + "\nANCHOR>>>\n"
            "Continue."
        )

    async def autopilot_run(
        self,
        initial_prompt: str = "BEGIN",
        max_chunks: Optional[int] = None,
        on_chunk=None,
        on_event=None,
        system_prompt: Optional[str] = None,
    ):
        """Run an autopilot loop with optional callbacks.
        on_chunk(idx: int, body: str, hint: Optional[str])
        on_event(type: str, payload: dict)
        """
        from .chunking import anchor_from_text, continuation_anchor, jaccard_ngrams

        first = True
        chunk_count = 0

        while max_chunks is None or chunk_count < max_chunks:
            if on_event:
                try:
                    on_event("chunk_start", {"idx": chunk_count + 1})
                except Exception:
                    pass

            # Decide next prompt
            if first:
                user_text = initial_prompt if initial_prompt != "BEGIN" else "BEGIN: Continue exactly from after the anchor; do not repeat or reintroduce; no summary."
                first = False
            else:
                if self.state.continuation_mode == "anchor":
                    anch = continuation_anchor(
                        self.state.history, self.state.anchor_length
                    )
                    if anch:
                        user_text = await self.build_anchor_continue_prompt(anch)
                        # Add coverage hammer for self-study runs
                        if (
                            getattr(self.state, "session_mode", None) == "zero2hero"
                            and getattr(self.state, "coverage_hammer_on", False)
                        ):
                            user_text += "\nDo not conclude or summarize; coverage is not complete. Continue teaching the field and its subfields to the target depth."
                    else:
                        user_text = "continue."
                else:
                    user_text = "continue."

            # First segment
            reply = await self.send_and_collect(user_text, system_prompt=system_prompt)
            body, hint = await self.strip_next_marker(
                reply
            )  # strip NEXT from main body; capture hint

            # Auto-extend within the same subtopic to hit OUTPUT_MIN_CHARS
            accumulated = body
            local_hint = hint
            micro = 0
            while (
                self.state.output_push_on
                and len(accumulated) < self.state.output_min_chars
                and micro < self.state.output_push_max_passes
            ):

                # Build a local anchor from the accumulated text
                local_anch = anchor_from_text(accumulated, self.state.anchor_length)
                ext_prompt = (
                    await self.build_anchor_continue_prompt(local_anch)
                    + "\nFill to the per-response output limit within this same subtopic. "
                    "Do not reintroduce or restart; continue exactly. "
                    "Do not write a NEXT line yet; do not conclude."
                )

                ext_reply = await self.send_and_collect(ext_prompt, system_prompt=system_prompt)
                ext_body, ext_hint = await self.strip_next_marker(
                    ext_reply
                )  # strip any premature NEXT
                if not ext_body.strip():
                    break

                # Optional repetition guard: stop if highly repetitive vs last portion
                if self.state.repetition_warn:
                    prev_tail = anchor_from_text(
                        accumulated, min(800, self.state.anchor_length * 4)
                    )
                    rep = jaccard_ngrams(
                        prev_tail,
                        ext_body[: max(400, self.state.anchor_length)],
                        n=self.state.repetition_ngram,
                    )
                    if rep > self.state.repetition_threshold:
                        print(
                            f"High repetition during extension (Jaccard~{rep:.2f}). Stopping extend."
                        )
                        break

                accumulated += (
                    "\n\n" if not accumulated.endswith("\n") else ""
                ) + ext_body
                if ext_hint:  # keep only the last NEXT if the final step later adds it
                    local_hint = ext_hint
                micro += 1

            # Now use the accumulated text as the final body for this iteration
            final_body = accumulated
            final_hint = local_hint

            # Optional repetition detection (vs previous chunk)
            if self.state.repetition_warn:
                prev_tail = continuation_anchor(
                    self.state.history, min(800, self.state.anchor_length * 4)
                )
                rep = jaccard_ngrams(
                    prev_tail,
                    final_body[: max(400, self.state.anchor_length)],
                    n=self.state.repetition_ngram,
                )
                if rep > self.state.repetition_threshold:
                    print(f"High repetition detected (Jaccard~{rep:.2f}).")

            chunk_count += 1
            if on_chunk:
                try:
                    on_chunk(chunk_count, final_body, final_hint)
                except Exception:
                    pass

            # Stop on explicit END
            if final_hint and final_hint.upper() in {"END", "DONE", "STOP", "FINISHED"}:
                print(f"NEXT: [{final_hint}] — stopping.")
                break

        print(f"Autopilot finished after {chunk_count} chunk(s).")
