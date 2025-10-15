"""Tests for prompt composition functionality."""
import pytest
from xsarena.core.prompt import compose_prompt


def test_compose_prompt():
    """Test prompt composition functionality."""
    composition = compose_prompt(
        subject="Test Subject",
        base="zero2hero",
        overlays=["no_bs"],
        extra_notes="Test extra notes",
        min_chars=2000,
        passes=1,
        max_chunks=8
    )
    
    assert hasattr(composition, 'system_text')
    assert isinstance(composition.system_text, str)
    assert len(composition.system_text) > 0
    assert "Test Subject" in composition.system_text


def test_compose_prompt_with_warnings():
    """Test prompt composition with warnings."""
    composition = compose_prompt(
        subject="Short",
        base="invalid_base",  # This should generate a warning
        overlays=["invalid_overlay"],  # This should generate a warning
        extra_notes="",
        min_chars=100,
        passes=0,
        max_chunks=1
    )
    
    # Even with invalid inputs, it should still return a composition
    assert hasattr(composition, 'system_text')
    assert isinstance(composition.system_text, str)