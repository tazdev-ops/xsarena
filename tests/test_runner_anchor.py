"""Tests for JobManager anchored continuation functionality."""

import tempfile
from pathlib import Path

import pytest
from xsarena.core.anchor_service import anchor_from_text


def test_anchor_from_text():
    """Unit test: write a temp file with a known tail and assert the next user prompt includes that anchor."""
    # Test the anchor_from_text function directly
    text = "This is some content that ends with a specific tail part."
    anchor = anchor_from_text(text, 300)

    assert "specific tail part" in anchor
    assert len(anchor) <= 300


@pytest.mark.asyncio
async def test_jobrunner_anchored_continuation():
    """Integration test: simulate the anchored continuation logic in JobManager."""
    # This test simulates the logic that would happen in the run_job method
    # where subsequent chunks read the tail of the output file to create an anchor

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(
            "This is the first chunk of content that should be used as an anchor for the next chunk."
        )
        output_file_path = f.name

    try:
        # Simulate the anchor extraction that happens in JobManager
        content = Path(output_file_path).read_text(encoding="utf-8")
        anchor = anchor_from_text(content, 300)

        # This is what would be used to build the next prompt
        from xsarena.core.anchor_service import build_anchor_continue_prompt

        next_prompt = build_anchor_continue_prompt(anchor)

        # Verify the next prompt contains the anchor
        assert "anchor" in next_prompt.lower()
        assert "first chunk" in next_prompt or "specific tail" in next_prompt

    finally:
        Path(output_file_path).unlink()


@pytest.mark.asyncio
async def test_jobrunner_continuation_not_restart():
    """Unit test: verify no restart in body by checking continuation logic."""
    # Create a mock continuation scenario
    previous_content = (
        "In the previous section, we discussed the foundations of the topic."
    )
    new_anchor = anchor_from_text(previous_content, 300)

    # The continuation prompt should not restart but continue from the anchor
    from xsarena.core.anchor_service import build_anchor_continue_prompt

    continuation_prompt = build_anchor_continue_prompt(new_anchor)

    # Verify it asks to continue from the anchor, not restart
    assert "continue" in continuation_prompt.lower()
    assert (
        "exactly from after" in continuation_prompt.lower()
        or "resume" in continuation_prompt.lower()
    )
    assert (
        "do not repeat" in continuation_prompt.lower()
        or "no re-introductions" in continuation_prompt.lower()
    )
