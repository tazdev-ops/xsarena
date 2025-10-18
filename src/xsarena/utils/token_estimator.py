"""Token estimation utilities for XSArena."""

import re


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text using a heuristic approach.
    This is a fast approximation that doesn't require external dependencies like tiktoken.
    The heuristic is roughly: tokens = chars / 4 for English text, with adjustments.
    """
    if not text:
        return 0

    # Basic estimation: ~4 characters per token for English text
    # But we'll use a more refined approach
    chars = len(text)

    # Count words (sequences of word characters)
    words = len(re.findall(r"\b\w+\b", text))

    # Use a weighted average: 1.3 tokens per word + 0.25 tokens per char
    # This gives us a reasonable approximation without heavy dependencies
    token_estimate = (words * 1.3) + (chars * 0.25)

    # Ensure we return an integer
    return max(1, int(token_estimate))


def chars_to_tokens_approx(chars: int, text_sample: str = "") -> int:
    """
    Convert character count to approximate token count.
    Uses a sample text to refine the estimation if provided.
    """
    if text_sample:
        char_count = len(text_sample)
        if char_count > 0:
            # Calculate the ratio from the sample
            sample_tokens = estimate_tokens(text_sample)
            ratio = sample_tokens / char_count
            return int(chars * ratio)

    # Default approximation: 4 chars per token
    return max(1, int(chars / 4))


def tokens_to_chars_approx(tokens: int, text_sample: str = "") -> int:
    """
    Convert token count to approximate character count.
    Uses a sample text to refine the estimation if provided.
    """
    if text_sample:
        char_count = len(text_sample)
        if char_count > 0:
            # Calculate the ratio from the sample
            sample_tokens = estimate_tokens(text_sample)
            if sample_tokens > 0:
                ratio = char_count / sample_tokens
                return int(tokens * ratio)

    # Default approximation: 4 chars per token
    return max(1, tokens * 4)
