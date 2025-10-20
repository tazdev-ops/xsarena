"""Common helper functions for XSArena."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import yaml


def is_binary_sample(b: bytes) -> bool:
    """Check if bytes look like binary content."""
    if not b:
        return False
    if b.count(0) > 0:
        return True
    # Heuristic: if too many non-text bytes
    text_chars = bytes(range(32, 127)) + b"\n\r\t\b\f"
    non_text_ratio = sum(ch not in text_chars for ch in b) / len(b)
    return non_text_ratio > 0.30


def safe_read_bytes(p: Path, max_bytes: int) -> Tuple[bytes, bool]:
    """Safely read bytes from a file with size limit."""
    try:
        data = p.read_bytes()
    except Exception:
        return b"", False
    truncated = False
    if len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True
    return data, truncated


def safe_read_text(p: Path, max_bytes: int) -> Tuple[str, bool]:
    """Safely read text from a file with size limit."""
    try:
        text = p.read_text("utf-8", errors="replace")
    except Exception:
        return "[ERROR READING FILE]", False
    truncated = False
    if len(text) > max_bytes:
        text = text[:max_bytes]
        truncated = True
    return text, truncated


def load_yaml_or_json(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a file that can be either YAML or JSON format.

    Args:
        path: Path to the file to load

    Returns:
        Dictionary with the loaded data
    """
    path = Path(path)

    try:
        # Try YAML first
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        # If YAML fails, try JSON
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def load_json_auto(path: str) -> Any:
    """
    Load JSON file that may be compressed (.json.gz) or plain (.json).

    Args:
        path: Path to the JSON file (without extension)

    Returns:
        Loaded JSON data
    """
    gz = path + ".gz"
    if os.path.exists(gz):
        import gzip

        with gzip.open(gz, "rt", encoding="utf-8") as f:
            return json.load(f)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_with_error_handling(path: Path) -> Dict[str, Any]:
    """
    Load JSON file with error handling, returning empty dict on failure.

    Args:
        path: Path to the JSON file

    Returns:
        Loaded JSON data or empty dict if loading fails
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_jsonc(jsonc_string: str) -> Dict[str, Any]:
    """
    Parse JSONC (JSON with comments) string by removing comments first.

    Args:
        jsonc_string: JSONC string to parse

    Returns:
        Parsed dictionary
    """
    # Remove single-line comments
    lines = jsonc_string.splitlines()
    clean_lines = []
    for line in lines:
        # Remove inline comments starting with //
        comment_pos = line.find("//")
        if comment_pos != -1:
            line = line[:comment_pos]
        # Only add non-empty lines after stripping whitespace
        if line.strip():
            clean_lines.append(line)

    clean_json = "\n".join(clean_lines)
    return json.loads(clean_json)
