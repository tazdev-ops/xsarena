"""Tests for chunking functionality."""

from xsarena.core.chunking import byte_chunk, continuation_anchor, jaccard_ngrams


def test_byte_chunk():
    """Test byte chunking functionality."""
    text = "This is a test text that will be chunked into smaller pieces."
    chunks = byte_chunk(text, max_bytes=20)

    assert len(chunks) > 0
    assert all(
        len(chunk.text.encode("utf-8")) <= 25 for chunk in chunks
    )  # Allow some buffer


def test_continuation_anchor():
    """Test continuation anchor extraction."""

    # Create mock history with messages
    class MockMessage:
        def __init__(self, role, content):
            self.role = role
            self.content = content

    history = [
        MockMessage("user", "Initial question"),
        MockMessage(
            "assistant", "First response with some content that should be anchored"
        ),
        MockMessage("user", "Follow-up question"),
        MockMessage("assistant", "Second response that continues from previous"),
    ]

    anchor = continuation_anchor(history, anchor_length=30)
    assert isinstance(anchor, str)
    assert len(anchor) > 0


def test_jaccard_ngrams():
    """Test Jaccard similarity calculation."""
    text1 = "This is a sample text for testing"
    text2 = "This is a sample text for testing"
    text3 = "This is completely different text"

    # Same text should have high similarity
    similarity_same = jaccard_ngrams(text1, text2, n=3)
    assert similarity_same == 1.0

    # Different text should have lower similarity
    similarity_diff = jaccard_ngrams(text1, text3, n=3)
    assert similarity_diff < 0.5
