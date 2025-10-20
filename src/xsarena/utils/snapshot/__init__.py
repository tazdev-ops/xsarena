"""XSArena snapshot utilities - modular components."""

from .builders import (
    build_git_context,
    build_jobs_summary,
    build_manifest,
    build_system_info,
    get_review_artifacts,
    get_rules_digest,
    sha256_bytes,
    ts_utc,
)
from .collectors import collect_git_files, collect_paths
from .config import read_snapshot_config
from .writers import write_pro_snapshot, write_text_snapshot, write_zip_snapshot

__all__ = [
    # Builders
    "build_git_context",
    "build_jobs_summary",
    "build_manifest",
    "build_system_info",
    "get_rules_digest",
    "get_review_artifacts",
    "sha256_bytes",
    "ts_utc",
    # Collectors
    "collect_paths",
    "collect_git_files",
    # Config
    "read_snapshot_config",
    # Writers
    "write_text_snapshot",
    "write_zip_snapshot",
    "write_pro_snapshot",
]
