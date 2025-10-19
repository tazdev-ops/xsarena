"""Tests for reading overlay functionality."""

from xsarena.core.prompt import compose_prompt
from xsarena.core.state import SessionState


def test_reading_overlay_state():
    """Test that SessionState has the reading_overlay_on attribute."""
    state = SessionState()

    # Check that the attribute exists and has the correct default value
    assert hasattr(state, "reading_overlay_on")
    assert state.reading_overlay_on is False  # Default should be False

    # Test setting the attribute
    state.reading_overlay_on = True
    assert state.reading_overlay_on is True

    print("✓ Reading overlay state test passed")


def test_reading_overlay_prompt_composition():
    """Test that prompt composition includes reading overlay when enabled."""
    # Create a state with reading overlay enabled
    state = SessionState()
    state.reading_overlay_on = True

    # Compose a prompt with the apply_reading_overlay parameter
    result = compose_prompt(
        subject="Test Subject", base="zero2hero", apply_reading_overlay=True
    )

    # Check that the reading overlay instruction is in the system text
    assert "DOMAIN-AWARE FURTHER READING" in result.system_text
    assert "Further Reading" in result.system_text
    assert "data/resource_map.en.json" in result.system_text

    # Check that the reading overlay is in the applied metadata
    assert "reading_overlay" in result.applied
    assert result.applied["reading_overlay"] is True

    print("✓ Reading overlay prompt composition test passed")


def test_reading_overlay_prompt_composition_disabled():
    """Test that prompt composition does not include reading overlay when disabled."""
    # Create a state with reading overlay disabled
    state = SessionState()
    state.reading_overlay_on = False

    # Compose a prompt with apply_reading_overlay disabled
    result = compose_prompt(
        subject="Test Subject", base="zero2hero", apply_reading_overlay=False
    )

    # Check that the reading overlay instruction is NOT in the system text
    assert "DOMAIN-AWARE FURTHER READING" not in result.system_text
    assert "Further Reading" not in result.system_text

    # Check that the reading overlay is not in the applied metadata
    assert (
        "reading_overlay" not in result.applied
        or result.applied.get("reading_overlay") is not True
    )

    print("✓ Reading overlay disabled prompt composition test passed")


def test_reading_overlay_without_state():
    """Test that prompt composition works without state (reading overlay disabled by default)."""
    # Compose a prompt without state
    result = compose_prompt(subject="Test Subject", base="zero2hero")

    # Check that the reading overlay instruction is NOT in the system text
    assert "DOMAIN-AWARE FURTHER READING" not in result.system_text
    assert "Further Reading" not in result.system_text

    print("✓ Prompt composition without state test passed")


def run_all_tests():
    """Run all reading overlay tests."""
    print("Running reading overlay tests...")

    test_reading_overlay_state()
    test_reading_overlay_prompt_composition()
    test_reading_overlay_prompt_composition_disabled()
    test_reading_overlay_without_state()

    print("All reading overlay tests passed! ✓")


if __name__ == "__main__":
    run_all_tests()
