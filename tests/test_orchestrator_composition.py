"""Tests for orchestrator composition meta - run_spec stores job.meta["system_text"] including overlays + extra file content."""

import tempfile
from pathlib import Path

from xsarena.core.prompt import compose_prompt
from xsarena.core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset


def test_orchestrator_composition_meta():
    """Test that run_spec composition creates proper system_text with overlays and extra notes."""
    # Test the prompt composition directly
    composition = compose_prompt(
        subject="Test Subject",
        base="zero2hero",
        overlays=["narrative", "no_bs"],
        extra_notes="Extra notes",
        min_chars=4200,
        passes=1,
        max_chunks=12,
    )

    system_text = composition.system_text

    # Check that the system text contains expected overlay elements
    assert (
        "narrative" in system_text.lower()
        or "PEDAGOGY & NARRATIVE OVERLAY" in system_text
    )
    assert (
        "plain" in system_text.lower()
        or "no fluff" in system_text.lower()
        or "LANGUAGE CONSTRAINTS" in system_text
    )

    # Check that extra notes are included
    assert "Extra notes" in system_text

    # Check that continuation rules are included
    assert "continue" in system_text.lower()


def test_runspec_extra_files_integration():
    """Test RunSpecV2 can handle extra files."""
    # Create a temporary extra file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is extra content from a file.")
        extra_file_path = f.name

    try:
        # Create a run spec with extra files
        run_spec = RunSpecV2(
            subject="Test Subject",
            length=LengthPreset.STANDARD,
            span=SpanPreset.MEDIUM,
            overlays=["narrative", "no_bs"],
            extra_note="Extra notes",
            extra_files=[extra_file_path],
            out_path="./test_output.md",
            profile="",
        )

        # Verify the spec was created properly
        assert run_spec.subject == "Test Subject"
        assert len(run_spec.extra_files) == 1
        assert extra_file_path in run_spec.extra_files

        # Test the resolved method
        resolved = run_spec.resolved()
        assert "min_length" in resolved
        assert "passes" in resolved
        assert "chunks" in resolved

    finally:
        # Clean up the temporary file
        Path(extra_file_path).unlink()
