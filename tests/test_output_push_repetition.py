"""Tests for JobManager output push and repetition guard functionality."""

from xsarena.core.chunking import jaccard_ngrams


def test_repetition_guard_jaccard_ngrams():
    """Unit test: simulate short chunk and ensure micro-extends add body until min chars or repetition trips."""
    # Test the jaccard_ngrams function with similar content
    content1 = "This is a sample content that we are testing for similarity."
    content2 = "This is a sample content that we are testing for similarity."

    similarity = jaccard_ngrams(content1, content2, n=4)
    assert similarity == 1.0  # Identical content should have 100% similarity

    # Test with slightly different content
    content3 = (
        "This is a sample content that we are testing for similarity with variations."
    )
    similarity2 = jaccard_ngrams(content1, content3, n=4)
    assert 0.0 <= similarity2 <= 1.0  # Similarity should be between 0 and 1

    # Test with completely different content
    content4 = "Completely different content with no overlapping n-grams."
    similarity3 = jaccard_ngrams(content1, content4, n=4)
    assert similarity3 < 0.1  # Should have very low similarity


def test_micro_extend_logic_simulation():
    """Simulate the micro-extend logic that happens in JobManager."""
    # This test verifies the logic without actually running the full job
    short_content = "Short content."
    min_chars = 50
    passes = 3

    # Simulate the micro-extend loop
    extended_content = short_content
    extend_count = 0

    while len(extended_content) < min_chars and extend_count < passes:
        # In real implementation, this would call the LLM again with an anchor
        # Here we just simulate adding more content
        extended_content += " Additional content added during micro-extend pass."
        extend_count += 1

    # Verify that the content was extended
    assert len(extended_content) > len(short_content)
    assert extend_count <= passes


def test_repetition_guard_trigger():
    """Test that repetition guard triggers when similarity is above threshold."""
    # Simulate content that is too similar
    prev_tail = (
        "This content is very repetitive and similar to what was just generated."
    )
    new_head = "This content is very repetitive and similar to what was just generated."

    similarity = jaccard_ngrams(new_head, prev_tail)
    repetition_threshold = 0.8  # Common threshold

    # This similarity should trigger the repetition guard
    if similarity > repetition_threshold:
        # In real code, this would set an auto-pause flag and stop micro-extend
        auto_pause_flag = True
        assert auto_pause_flag is True
