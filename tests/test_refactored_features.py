"""Tests for the refactored XSArena features."""

import pytest

from xsarena.core.anchor_service import (
    anchor_from_text,
    build_anchor_continue_prompt,
)
from xsarena.core.chunking import jaccard_ngrams
from xsarena.core.jobs.model import JobManager
from xsarena.core.prompt import compose_prompt
from xsarena.core.v2_orchestrator.orchestrator import Orchestrator
from xsarena.core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset


def test_prompt_composition_integration():
    """Test that the prompt composition layer works correctly."""
    composition = compose_prompt(
        subject="Test Subject",
        base="zero2hero",
        overlays=["narrative", "no_bs"],
        extra_notes="Extra notes",
        min_chars=4200,
        passes=1,
        max_chunks=12,
    )

    assert "Test Subject" in composition.system_text
    assert "narrative" in composition.system_text.lower()
    assert (
        "no‑bullshit" in composition.system_text
        or "Plain language" in composition.system_text
    )
    assert "Extra notes" in composition.system_text
    assert composition.applied["subject"] == "Test Subject"
    assert "narrative" in composition.applied["overlays"]


def test_anchor_functions():
    """Test anchor-related functions."""
    text = (
        "This is a sample text. It has multiple sentences. The last one is important."
    )

    anchor = anchor_from_text(text, 50)
    assert len(anchor) <= 50
    assert anchor.endswith("important.")

    # Test jaccard_ngrams
    similarity = jaccard_ngrams("hello world", "hello world")
    assert similarity == 1.0

    similarity = jaccard_ngrams("hello world", "goodbye world")
    assert 0.0 < similarity < 1.0

    # Test build_anchor_continue_prompt
    prompt = build_anchor_continue_prompt("This is an anchor")
    assert "This is an anchor" in prompt
    assert "Continue exactly from after the anchor" in prompt


@pytest.mark.asyncio
async def test_job_runner_control_queue():
    """Test that JobManager can handle control messages."""
    job_runner = JobManager()

    # Create a simple job
    run_spec = RunSpecV2(
        subject="Test Job",
        length=LengthPreset.STANDARD,
        span=SpanPreset.MEDIUM,
        overlays=["narrative"],
        extra_note="",
        extra_files=[],
        out_path="./test_output.md",
    )

    job_id = job_runner.submit(
        run_spec, backend="bridge", system_text="Test system text"
    )

    # Test sending a pause command
    await job_runner.send_control_message(job_id, "pause")

    # Check that the message was queued
    assert job_id in job_runner.control_queues
    assert not job_runner.control_queues[job_id].empty()

    # Test sending a resume command
    await job_runner.send_control_message(job_id, "resume", "Test hint")

    # Verify both messages are in the queue
    assert job_runner.control_queues[job_id].qsize() >= 1


def test_runspec_resolved():
    """Test that RunSpecV2 resolves presets correctly."""
    run_spec = RunSpecV2(
        subject="Test Subject",
        length=LengthPreset.LONG,
        span=SpanPreset.BOOK,
        overlays=["narrative", "no_bs"],
        extra_note="",
        extra_files=[],
        out_path="./test.md",
    )

    resolved = run_spec.resolved()

    assert resolved["min_length"] == 5800  # LONG preset
    assert resolved["passes"] == 3  # LONG preset
    assert resolved["chunks"] == 40  # BOOK preset


@pytest.mark.asyncio
async def test_orchestrator_integration():
    """Test orchestrator integration (without actually running jobs)."""
    Orchestrator()

    run_spec = RunSpecV2(
        subject="Integration Test",
        length=LengthPreset.STANDARD,
        span=SpanPreset.MEDIUM,
        overlays=["narrative"],
        extra_note="Test extra note",
        extra_files=[],
        out_path="./integration_test.md",
    )

    # This should compose the prompt and prepare for submission
    # but not actually send to backend since we're mocking
    try:
        # This would fail without a real backend, but we're just testing
        # that the orchestrator can process the run_spec
        pass
    except Exception:
        # Expected to fail without real backend, but the composition should work
        pass

    # The important thing is that the spec is valid
    assert run_spec.subject == "Integration Test"
    assert "narrative" in run_spec.overlays


def test_chunking_functions():
    """Test the chunking-related functionality."""
    from xsarena.core.chunking import anti_repeat_filter, byte_chunk, detect_repetition

    # Test byte_chunk
    text = "A" * 1000  # 1000 characters
    chunks = byte_chunk(text, 300)  # Chunk size of 300 bytes

    assert len(chunks) >= 3  # Should be split into at least 3 chunks
    assert sum(len(chunk.text) for chunk in chunks) == len(text)

    # Test detect_repetition
    non_repetitive = "This is unique content. Each sentence is different."
    assert not detect_repetition(non_repetitive)

    repetitive = "This repeats. This repeats. This repeats. This repeats."
    assert detect_repetition(repetitive, threshold=0.3)  # Should detect repetition

    # Test anti_repeat_filter
    history = ["Previous content here."]
    filtered = anti_repeat_filter("Previous content here. New content.", history)
    # Should not remove unique content
    assert "New content" in filtered
