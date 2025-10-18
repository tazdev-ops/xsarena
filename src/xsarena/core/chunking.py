"""Text chunking and anchor management for XSArena."""

from dataclasses import dataclass
from typing import List

from .anchor_service import anchor_from_text


@dataclass
class Chunk:
    """A text chunk with metadata."""

    text: str
    start_pos: int
    end_pos: int
    index: int


def byte_chunk(text: str, max_bytes: int) -> List[Chunk]:
    """Split text into chunks of approximately max_bytes size."""
    chunks = []
    start = 0
    index = 0

    while start < len(text):
        # Find a good break point near the max_bytes limit
        end = start + max_bytes

        if end >= len(text):
            end = len(text)
        else:
            # Try to break at sentence or paragraph boundary
            chunk_text = text[start:end]
            last_sentence = chunk_text.rfind(".")
            last_paragraph = chunk_text.rfind("\n\n")

            if last_paragraph > max_bytes * 0.7:
                end = start + last_paragraph + 2
            elif last_sentence > max_bytes * 0.7:
                end = start + last_sentence + 1

        chunks.append(
            Chunk(text=text[start:end], start_pos=start, end_pos=end, index=index)
        )

        start = end
        index += 1

    return chunks


def detect_repetition(text: str, threshold: float = 0.8) -> bool:
    """Detect if there's excessive repetition in the text."""
    if len(text) < 100:
        return False

    # Simple repetition detection based on n-grams
    words = text.split()
    if len(words) < 10:
        return False

    # Check for repeated sequences of 5-10 words
    for seq_len in range(5, min(11, len(words) // 2)):
        for i in range(len(words) - seq_len * 2):
            seq = " ".join(words[i : i + seq_len])
            next_seq = " ".join(words[i + seq_len : i + seq_len * 2])

            if seq == next_seq:
                # Found a repetition, calculate how significant it is
                rep_words = seq_len * 2
                if rep_words / len(words) > threshold / 10:
                    return True

    return False


def anti_repeat_filter(text: str, history: List[str]) -> str:
    """Filter out repetitive content based on history."""
    if not history:
        return text

    # Simple approach: remove content that closely matches recent history
    for hist_item in reversed(history[-3:]):  # Check last 3 history items
        if hist_item and text.startswith(hist_item[: len(hist_item) // 2]):
            # Remove the repeated part
            text = text[len(hist_item) // 2 :]
            break

    # Remove repeated paragraphs
    paragraphs = text.split("\n\n")
    unique_paragraphs = []
    for para in paragraphs:
        if para.strip() not in unique_paragraphs:
            unique_paragraphs.append(para.strip())

    return "\n\n".join(unique_paragraphs)


def jaccard_ngrams(a: str, b: str, n: int = 4) -> float:
    """Calculate Jaccard similarity between two strings using n-grams."""

    def ngrams(x):
        x = " ".join(x.split())  # normalize whitespace
        return {x[i : i + n] for i in range(0, max(0, len(x) - n + 1))}

    A, B = ngrams(a), ngrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def continuation_anchor(history: List["Message"], anchor_length: int = 300) -> str:
    """Get the continuation anchor from the last assistant message."""
    if not history:
        return ""

    # Find the last assistant message
    for msg in reversed(history):
        if msg.role == "assistant":
            prev = msg.content or ""
            if not prev:
                return ""
            return anchor_from_text(prev, anchor_length)

    return ""
