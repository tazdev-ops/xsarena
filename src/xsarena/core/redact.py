"""Redaction utilities for XSArena."""

import re

# Define redaction patterns - shared with snapshot redaction
REDACTION_PATTERNS = [
    # API keys, secrets, tokens, passwords
    (
        re.compile(
            r'(?i)(api[_-]?key|secret|token|password|pwd|auth|bearer)[\s:=]+\s*["\']?([A-Za-z0-9_\-]{16,})["\']?',
            re.IGNORECASE,
        ),
        r'\1="[REDACTED]"',
    ),
    # Email addresses
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    # IP addresses
    (re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"), "[REDACTED_IP]"),
    # URLs with potential sensitive parameters
    (
        re.compile(r'https?://[^\s<>"]*(?:[?&](?:[A-Za-z0-9_-]+=[^&\s<>"\']*)*)*'),
        "[REDACTED_URL]",
    ),
    # Long alphanumeric strings (likely tokens)
    (re.compile(r"\b[A-Za-z0-9]{30,}\b"), "[REDACTED_LONG_TOKEN]"),
]


def redact(text: str) -> str:
    """
    Redact sensitive information from text.

    Args:
        text: Input text to redact

    Returns:
        Redacted text with sensitive information replaced
    """
    if not text:
        return text

    redacted_text = text
    for pattern, replacement in REDACTION_PATTERNS:
        redacted_text = pattern.sub(replacement, redacted_text)

    return redacted_text


def redact_snapshot_content(content: str) -> str:
    """
    Apply redaction to snapshot content using the same patterns as runtime redaction.

    Args:
        content: Content to redact

    Returns:
        Redacted content
    """
    return redact(content)
