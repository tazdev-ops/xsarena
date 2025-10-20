"""
Simple snapshot utility for XSArena with minimal dependencies.

Zero dependencies; optional tomllib if present; otherwise default modes (minimal/standard/full).
Best-effort Git context and Jobs summary; never fatal.
Text or Zip output; truncates large files per max_size; optional redact.
"""

# Re-export functions from the new modules to maintain backward compatibility
from .snapshot.config import read_snapshot_config
from .snapshot.collectors import collect_paths, collect_git_files
from .snapshot.builders import (
    build_git_context, 
    build_jobs_summary, 
    build_manifest, 
    build_system_info, 
    get_rules_digest, 
    get_review_artifacts, 
    ts_utc, 
    rel_posix
)
from .snapshot.writers import write_text_snapshot, write_zip_snapshot, write_pro_snapshot
from .helpers import is_binary_sample, safe_read_bytes, safe_read_text

# Import remaining functions that are not in the new modules
import hashlib
import json
import os
import platform
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Set, Tuple

try:
    import tomllib  # Python 3.11+
except ImportError:
    tomllib = None

ROOT = Path.cwd()


def sha256_bytes(b: bytes) -> str:
    """Calculate SHA256 hash of bytes."""
    return hashlib.sha256(b).hexdigest()


def get_snapshot_digest(output_content: str) -> str:
    """Get combined snapshot digest for integrity verification."""
    return f"Snapshot Integrity Digest (SHA256 of entire snapshot): {sha256_bytes(output_content.encode('utf-8'))}\n"


def render_directory_tree(
    path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0
) -> str:
    """Render a directory tree up to a specified depth."""
    if current_depth > max_depth:
        return ""

    tree_lines = []
    if current_depth == 0:
        tree_lines.append(f"{path.name}/")
    else:
        tree_lines.append(f"{prefix}├── {path.name}/")

    if path.is_dir():
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "

            if item.is_dir():
                if current_depth < max_depth:
                    tree_lines.append(f"{prefix}{extension}{connector}{item.name}/")
                    tree_lines.append(
                        render_directory_tree(
                            item, prefix + extension, max_depth, current_depth + 1
                        )
                    )
            else:
                tree_lines.append(f"{prefix}{extension}{connector}{item.name}")

    return "\n".join(line for line in tree_lines if line)


def get_directory_listings() -> str:
    """Get directory listings for important paths."""
    important_paths = [
        ROOT / "src",
        ROOT / "docs",
        ROOT / "directives",
        ROOT / "recipes",
        ROOT / "tools",
        ROOT / "data",
        ROOT / ".xsarena",
    ]

    listings = []
    for path in important_paths:
        if path.exists():
            listings.append(f"\nDirectory listing for {path.name}/:")
            listings.append(render_directory_tree(path, max_depth=2))

    return "Directory Listings:\n" + "\n".join(listings) + "\n"