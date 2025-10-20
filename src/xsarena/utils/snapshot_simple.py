"""
Simple snapshot utility for XSArena with minimal dependencies.

This module re-exports the modularized snapshot functionality.
"""

# Re-export from modular components
from .snapshot.builders import (
    build_git_context,
    build_jobs_summary,
    build_manifest,
    build_system_info,
    get_review_artifacts,
    get_rules_digest,
    sha256_bytes,
    ts_utc,
)
from .snapshot.collectors import collect_git_files, collect_paths
from .snapshot.config import read_snapshot_config
from .snapshot.writers import (
    write_pro_snapshot,
    write_text_snapshot,
    write_zip_snapshot,
)

__all__ = [
    # Config
    "read_snapshot_config",
    # Collectors
    "collect_paths",
    "collect_git_files",
    # Writers
    "write_text_snapshot",
    "write_zip_snapshot",
    "write_pro_snapshot",
    # Builders
    "build_git_context",
    "build_jobs_summary",
    "build_manifest",
    "build_system_info",
    "get_rules_digest",
    "get_review_artifacts",
    "sha256_bytes",
    "ts_utc",
]
