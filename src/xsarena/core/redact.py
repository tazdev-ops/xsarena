"""Redaction utilities for XSArena."""

import re

# Define redaction patterns - shared with snapshot redaction
REDACTION_PATTERNS = [
    # API keys, secrets, tokens, passwords
    (
        re.compile(
            r"(?i)(api[_-]?key|secret|token|password|pwd|auth|bearer)[\s:=]+\s*['\"]?([A-Za-z0-9_\-]{16,})['\"]?",
            re.IGNORECASE,
        ),
        r"\\1=\"[REDACTED]\"",
    ),
    # Email addresses
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    # IP addresses (IPv4)
    (re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"), "[REDACTED_IP]"),
    # IPv6 addresses (various formats)
    (re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"), "[REDACTED_IPV6]"),
    (
        re.compile(r"\b(?:::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4})\b"),
        "[REDACTED_IPV6]",
    ),
    (
        re.compile(
            r"\b(?:[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4})\b"
        ),
        "[REDACTED_IPV6]",
    ),
    # URLs with potential sensitive parameters
    (
        re.compile(r"https?://[^\s<>\"']*(?:[?&](?:[A-Za-z0-9_-]+=[^&\s<>\"']*)*)*"),
        "[REDACTED_URL]",
    ),
    # JWT tokens
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b"),
        "[REDACTED_JWT]",
    ),
    # Long alphanumeric strings (likely tokens)
    (re.compile(r"\b[A-Za-z0-9]{30,}\b"), "[REDACTED_LONG_TOKEN]"),
    # AWS-style access keys (multiple formats)
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),  # Standard AWS access key
    (
        re.compile(r"(?i)(ASIA|AGPA)[0-9A-Z]{16}"),
        "[REDACTED_AWS_KEY]",
    ),  # AWS STS/Role access keys
    (
        re.compile(
            r"(?i)aws[_-]?(secret[_-]?)?access[_-]?key[\s:=]+\s*['\"][a-zA-Z0-9/+]{20,}['\"]"
        ),
        "[REDACTED_AWS_SECRET]",
    ),  # AWS secret access key
    # Phone numbers (various formats)
    (
        re.compile(
            r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
        ),
        "[REDACTED_PHONE]",
    ),  # US format
    (
        re.compile(
            r"\b(?:\+?\d{1,3}[-.\s]?)?\(?[0-9]{3,4}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{4,}\b"
        ),
        "[REDACTED_PHONE]",
    ),  # General format
    # Credit card numbers (basic patterns)
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CC]"),  # Basic CC format
    (re.compile(r"\b(?:\d{4}[-\s]?){2}\d{7}\b"), "[REDACTED_CC]"),  # Alternative format
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
