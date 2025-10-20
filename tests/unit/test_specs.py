"""Tests for run specifications."""
import pytest

from xsarena.core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset


def test_run_spec_resolved():
    spec = RunSpecV2(subject="Test", length=LengthPreset.LONG, span=SpanPreset.BOOK)
    resolved = spec.resolved()
    assert "min_length" in resolved
    assert "passes" in resolved
    assert "chunks" in resolved
    assert resolved["chunks"] == 40  # book span


def test_run_spec_validation():
    """Test that extra fields are forbidden."""
    with pytest.raises(ValueError):
        RunSpecV2(subject="Test", invalid_field="value")
