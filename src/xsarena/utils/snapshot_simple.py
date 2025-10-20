"""
Simple snapshot utility for XSArena with minimal dependencies.

This module re-exports the modularized snapshot functionality.
"""

# Re-export from modular components
from .snapshot.config import read_snapshot_config
from .snapshot.collectors import collect_paths, collect_git_files
from .snapshot.writers import write_text_snapshot, write_zip_snapshot, write_pro_snapshot
from .snapshot.builders import (
    build_git_context,
    build_jobs_summary,
    build_manifest,
    build_system_info,
    get_rules_digest,
    get_review_artifacts,
    sha256_bytes,
    ts_utc,
)

__all__ = [
    # Config
    'read_snapshot_config',
    # Collectors
    'collect_paths',
    'collect_git_files',
    # Writers
    'write_text_snapshot',
    'write_zip_snapshot',
    'write_pro_snapshot',
    # Builders
    'build_git_context',
    'build_jobs_summary',
    'build_manifest',
    'build_system_info',
    'get_rules_digest',
    'get_review_artifacts',
    'sha256_bytes',
    'ts_utc',
]
