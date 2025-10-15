# src/xsarena/core/engine.py
import re
import asyncio
from typing import Callable, Dict, List, Optional
from .backends import Backend, Message
from .chunking import anchor_from_text, continuation_anchor, jaccard_ngrams
from .state import SessionState

class Engine:
    def __init__(self, backend: Backend, state: SessionState):
        self.backend = backend
        self.state = state
        self.redaction_filter: Optional[Callable[[str], str]] = None

    async def send_and_collect(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))

        history_start = max(0, len(self.state.history) - self.state.window_size)
        messages.extend(self.state.history[history_start:])
        messages.append(Message(role="user", content=user_prompt))

        if self.redaction_filter:
            for msg in messages:
                msg.content = self.redaction_filter(msg.content)

        response = await self.backend.send(messages)
        
        self.state.add_message("user", user_prompt)
        self.state.add_message("assistant", response)

        if self.state.continuation_mode == "anchor":
            self.state.add_anchor(response)

        return response

    def set_redaction_filter(self, filter_func: Optional[Callable[[str], str]]):
        self.redaction_filter = filter_func

    async def build_anchor_continue_prompt(self, anchor: str) -> str:
        return f"Continue exactly from after the anchor; do not repeat or reintroduce; no summary.\nANCHOR:\n<<<ANCHOR\n{anchor}\nANCHOR>>>\nContinue."
    
    @staticmethod
    def strip_next_marker(text: str) -> tuple[str, str | None]:
        match = re.search(r"^\s*NEXT:\s*(.+)\s*$", text, re.MULTILINE)
        if match:
            hint = match.group(1).strip()
            # normalize hints like "[END]" -> "END"
            if hint.startswith("[") and hint.endswith("]"):
                hint = hint[1:-1].strip()
            text = text[:match.start()] + text[match.end():]
            return text.rstrip(), hint
        return text.rstrip(), None

    async def autopilot_run(
        self,
        initial_prompt: str,
        max_chunks: Optional[int],
        on_chunk: Optional[Callable[[int, str, Optional[str]], None]] = None,
        system_prompt: Optional[str] = None,
        on_event: Optional[Callable[[str, Dict], None]] = None,
    ):
        first = True
        chunk_count = 0
        while max_chunks is None or chunk_count < max_chunks:
            if first:
                user_text = initial_prompt
                first = False
            else:
                anch = continuation_anchor(self.state.history, self.state.anchor_length)
                user_text = await self.build_anchor_continue_prompt(anch) if anch else "continue."
                if self.state.session_mode == "zero2hero" and self.state.coverage_hammer_on:
                    user_text += "\nDo not conclude or summarize; coverage is not complete."

            reply = await self.send_and_collect(user_text, system_prompt=system_prompt)
            body, hint = self.strip_next_marker(reply)
            
            accumulated = body
            micro = 0
            while self.state.output_push_on and len(accumulated) < self.state.output_min_chars and micro < self.state.output_push_max_passes:
                local_anch = anchor_from_text(accumulated, self.state.anchor_length)
                ext_prompt = await self.build_anchor_continue_prompt(local_anch) + "\nFill to the per-response output limit within this same subtopic."
                
                ext_reply = await self.send_and_collect(ext_prompt, system_prompt=system_prompt)
                ext_body, ext_hint = self.strip_next_marker(ext_reply)
                if not ext_body.strip(): break
                
                if self.state.repetition_warn:
                    prev_tail = anchor_from_text(accumulated, min(800, self.state.anchor_length * 4))
                    rep = jaccard_ngrams(prev_tail, ext_body, n=self.state.repetition_ngram)
                    if rep > self.state.repetition_threshold:
                        print(f"Repetition detected (Jaccard~{rep:.2f}). Stopping extension.")
                        break
                
                accumulated += "\n\n" + ext_body
                if ext_hint: hint = ext_hint
                micro += 1
            
            final_body, final_hint = accumulated, hint
            chunk_count += 1
            if on_chunk:
                on_chunk(chunk_count, final_body, final_hint)
            if on_event:
                on_event("chunk_done", {"idx": chunk_count, "bytes": len(final_body)})
            
            if final_hint and final_hint.upper() in {"END", "DONE", "STOP"}:
                if on_event:
                    on_event("end_detected", {"hint": final_hint})
                print(f"NEXT: [{final_hint}] detected — stopping.")
                break
