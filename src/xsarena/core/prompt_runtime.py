"""Runtime utilities for prompt construction and management."""

from typing import Optional


def build_chunk_prompt(
    chunk_idx: int,
    job: "JobV3",
    session_state: Optional["SessionState"] = None,
    next_hint: Optional[str] = None,
    anchor: Optional[str] = None,
) -> str:
    """
    Build the user prompt for a specific chunk based on the current state and context.

    Args:
        chunk_idx: Current chunk index (1-based)
        job: The current job object
        session_state: Optional session state with configuration
        next_hint: Optional hint from previous chunks
        anchor: Optional text anchor for continuation

    Returns:
        The constructed user prompt string
    """
    from ..anchor_service import build_anchor_continue_prompt

    # For the first chunk, use a "BEGIN" style seed
    if chunk_idx == 1:
        hint_now = next_hint
        user_content = hint_now or "BEGIN"
        if hint_now:
            # Log hint application if needed
            pass  # Caller should handle logging

        # Apply outline-first toggle for the first chunk only if enabled
        if session_state and getattr(session_state, "outline_first_enabled", False):
            user_content = "BEGIN\nOUTLINE-FIRST SCAFFOLD\n- First chunk: produce a chapter-by-chapter outline consistent with the subject; end with NEXT: [Begin Chapter 1].\n- Subsequent chunks: follow the outline; narrative prose; define terms once; no bullet walls."
    else:
        # For subsequent chunks, implement anchored continuation
        user_content = build_anchor_continue_prompt(anchor) if anchor else ""

        # Override with next_hint if available
        if next_hint:
            user_content = next_hint

    # Add coverage hammer text if enabled in session state (after first chunk)
    if (
        chunk_idx > 1
        and session_state
        and getattr(session_state, "coverage_hammer_on", False)
    ):
        user_content += "\nCOVERAGE HAMMER: no wrap-up; continue to target depth."

    return user_content
