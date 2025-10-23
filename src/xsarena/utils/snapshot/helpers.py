"""Helper functions for snapshot operations."""

import fnmatch
import os
import posixpath
import re
from pathlib import Path
from typing import Callable, List, Union

# Precompiled regex patterns for redaction
API_KEY_PATTERN = re.compile(
    r"(\b[Aa]pi[Kk]ey[\"\']?\s*[:=]\s*[\"\']?)[^\"\',\s]{20,}([\"\']?)"
)
PASSWORD_PATTERN = re.compile(
    r"(\b[Pp]assword[\"\']?\s*[:=]\s*[\"\']?)[^\"\',\s]+([\"\']?)"
)
TOKEN_PATTERN = re.compile(
    r"(\b[Tt]oken[\"\']?\s*[:=]\s*[\"\']?)[^\"\',\s]{20,}([\"\']?)"
)
ACCESS_KEY_ID_PATTERN = re.compile(
    r"(\b[Aa]ccess[Kk]ey[Ii]d[\"\']?\s*[:=]\s*[\"\']?)[A-Z0-9]{10,}([\"\']?)"
)
SECRET_ACCESS_KEY_PATTERN = re.compile(
    r"(\b[Ss]ecret[Aa]ccess[Kk]ey[\"\']?\s*[:=]\s*[\"\']?)[^\"\',\s]{20,}([\"\']?)"
)


def _posix(path: Union[str, Path]) -> str:
    """Convert a file path to POSIX format for consistent comparison (used by flatpack_txt)."""
    return posixpath.normpath(str(path).replace(os.sep, "/"))


def posix_path_normalize(path: Union[str, Path]) -> str:
    """Convert a file path to POSIX format for consistent comparison."""
    return posixpath.normpath(str(path).replace(os.sep, "/"))


def _is_excluded(path: str, exclude_patterns: List[str]) -> bool:
    """Check if a path matches any exclude pattern (used by flatpack_txt)."""
    normalized_path = _posix(path)
    return any(
        fnmatch.fnmatch(normalized_path, pattern) for pattern in exclude_patterns
    )


def exclusion_predicate(disallow_globs: List[str]) -> Callable[[str], bool]:
    """Create a function that checks if a path matches any disallowed glob pattern."""

    def should_exclude(path: str) -> bool:
        """Check if path should be excluded based on disallow patterns."""
        normalized_path = posix_path_normalize(path)
        return any(
            fnmatch.fnmatch(normalized_path, pattern) for pattern in disallow_globs
        )

    return should_exclude


def expand_includes(root: Path, patterns: List[str]) -> set:
    """Expand glob patterns to a set of files."""
    out: set = set()
    for pat in patterns:
        for p in root.glob(pat):
            if p.is_file():
                out.add(p)
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        out.add(f)
    return out


def apply_redaction(content: str) -> str:
    """Apply redaction to sensitive content in snapshots."""
    # Apply precompiled patterns for redaction
    content = API_KEY_PATTERN.sub(r"\1[REDACTED_API_KEY]\2", content)
    content = PASSWORD_PATTERN.sub(r"\1[REDACTED_PASSWORD]\2", content)
    content = TOKEN_PATTERN.sub(r"\1[REDACTED_TOKEN]\2", content)
    content = ACCESS_KEY_ID_PATTERN.sub(r"\1[REDACTED_ACCESS_KEY_ID]\2", content)
    content = SECRET_ACCESS_KEY_PATTERN.sub(
        r"\1[REDACTED_SECRET_ACCESS_KEY]\2", content
    )

    return content
