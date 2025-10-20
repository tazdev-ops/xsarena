"""
File collection logic for XSArena snapshot utility.
"""

import subprocess
from pathlib import Path, PurePosixPath
from typing import List, Set, Tuple

from .config import ROOT, read_snapshot_config


def _matches(rel: str, pattern: str) -> bool:
    """Check if a relative path matches a glob pattern."""
    # Use PurePosixPath.match for proper ** handling; strip leading '/'
    pat = pattern.lstrip("/")
    return PurePosixPath(rel).match(pat)


def _expand_patterns(root: Path, patterns: List[str]) -> Set[Path]:
    """Expand glob patterns to a set of files."""
    out: Set[Path] = set()
    for pat in patterns:
        for p in root.glob(pat):
            if p.is_file():
                out.add(p)
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        out.add(f)
    return out


def _split_reinclude(patterns: List[str]) -> Tuple[List[str], List[str]]:
    """Split patterns into normal and re-include patterns."""
    normal, reincludes = [], []
    for p in patterns:
        if p.startswith("!"):
            reincludes.append(p[1:])
        else:
            normal.append(p)
    return normal, reincludes


def _apply_excludes(
    candidates: Set[Path], exclude_patterns: List[str], reincludes: List[str]
) -> Set[Path]:
    """Apply exclude patterns and re-include patterns to a set of candidate files."""
    rels = {str(p.relative_to(ROOT)): p for p in candidates}
    keep: dict = {}
    for rel, p in rels.items():
        if any(_matches(rel, ex) for ex in exclude_patterns):
            continue
        keep[rel] = p
    # Re-includes win: expand and add back even if excluded
    if reincludes:
        for p in _expand_patterns(ROOT, reincludes):
            if p.is_file():
                keep[str(p.relative_to(ROOT))] = p
    return set(keep.values())


def collect_paths(
    mode: str, include_git_tracked: bool = False, include_untracked: bool = False
) -> List[Path]:
    """Collect paths based on mode and git options."""
    cfg = read_snapshot_config()

    if include_git_tracked:
        return collect_git_files(
            include_untracked, cfg.get("modes", {}).get(mode, {}).get("exclude", [])
        )

    # Handle max mode differently - include everything except excludes
    if mode == "max":
        include_patterns = ["**/*"]
        exclude_patterns = []
    else:
        # Get mode-specific patterns
        mode_config = cfg.get("modes", {}).get(mode, {})
        include_patterns = mode_config.get("include", [])
        exclude_patterns = mode_config.get("exclude", [])

    # Add default excludes (these are always applied)
    default_excludes = [
        ".git/**",
        ".svn/**",
        ".hg/**",
        ".idea/**",
        ".vscode/**",
        "venv/**",
        ".venv/**",
        "__pycache__/**",
        ".pytest_cache/**",
        ".mypy_cache/**",
        ".ruff_cache/**",
        ".cache/**",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.o",
        "*.a",
        "*.so",
        "*.dll",
        "*.dylib",
        "*.log",
        "logs/**",
        ".xsarena/**",
        "*.egg-info/**",
        ".ipynb_checkpoints/**",
    ]

    all_excludes = exclude_patterns + default_excludes
    exclude_norm, reincludes = _split_reinclude(all_excludes)

    candidates = _expand_patterns(ROOT, include_patterns)
    files = _apply_excludes(candidates, exclude_norm, reincludes)
    return sorted(files)


def collect_git_files(
    include_untracked: bool, exclude_patterns: List[str]
) -> List[Path]:
    """Collect git-tracked files."""
    if not (ROOT / ".git").exists():
        return []

    files: Set[Path] = set()
    try:
        tracked = subprocess.check_output(
            ["git", "ls-files"], cwd=ROOT, text=True
        ).splitlines()
        for rel in tracked:
            p = (ROOT / rel).resolve()
            if p.is_file():
                files.add(p)
        if include_untracked:
            others = subprocess.check_output(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=ROOT,
                text=True,
            ).splitlines()
            for rel in others:
                p = (ROOT / rel).resolve()
                if p.is_file():
                    files.add(p)
    except Exception:
        pass

    # Apply excludes
    exclude_norm, reincludes = _split_reinclude(exclude_patterns)
    files = _apply_excludes(files, exclude_norm, reincludes)
    return sorted(files)