from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import yaml

DEFAULT_PRESETS = {
    "minimal": {
        "include": [
            "README.md",
            "COMMANDS_REFERENCE.md",
            "pyproject.toml",
            "src/xsarena/core/prompt.py",
            "src/xsarena/core/prompt_runtime.py",
            "src/xsarena/core/v2_orchestrator/orchestrator.py",
            "src/xsarena/core/v2_orchestrator/specs.py",
            "src/xsarena/core/jobs/model.py",
            "src/xsarena/core/jobs/executor.py",
            "src/xsarena/core/jobs/scheduler.py",
            "src/xsarena/core/jobs/store.py",
            "directives/base/zero2hero.md",
            "directives/system/plan_from_seeds.md",
            "directives/_rules/rules.merged.md",
        ],
        "exclude": [],
    },
    "normal": {
        "include": [
            "README.md",
            "COMMANDS_REFERENCE.md",
            "pyproject.toml",
            "src/xsarena/**",
            "docs/USAGE.md",
            "docs/OPERATING_MODEL.md",
        ],
        "exclude": [],
    },
    "maximal": {
        "include": ["**/*"],
        "exclude": [],
    },
}

DEFAULT_EXCLUDES = [
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
    "*.log",
    "logs/**",
    ".xsarena/**",
    "*.egg-info/**",
    ".ipynb_checkpoints/**",
    "books/**",
    "review/**",
    "tests/**",
    "examples/**",
    "packaging/**",
    "pipelines/**",
    "tools/**",
    "scripts/**",
    "repo_flat.txt",
    "xsa_snapshot*.txt",
    "xsa_snapshot*.zip",
    "xsa_debug_report*.txt",
    "snapshot_chunks/**",
]


def load_snapshot_presets() -> Tuple[Dict[str, Dict[str, List[str]]], List[str]]:
    """Load presets from .xsarena/config.yml under snapshot_presets key; fall back to sane defaults."""
    # First try to load from main config file under snapshot_presets key
    main_config_path = Path(".xsarena/config.yml")
    if main_config_path.exists():
        try:
            data = yaml.safe_load(main_config_path.read_text(encoding="utf-8")) or {}
            snapshot_data = data.get("snapshot_presets") or {}
            presets = snapshot_data.get("presets") or {}
            default_excludes = snapshot_data.get("default_excludes") or DEFAULT_EXCLUDES
            # normalize shapes
            norm = {}
            for name, spec in presets.items():
                inc = spec.get("include", []) or []
                exc = spec.get("exclude", []) or []
                norm[name.lower()] = {"include": list(inc), "exclude": list(exc)}
            if norm:  # Only return if we found custom presets
                return (norm, default_excludes)
        except Exception:
            pass

    # Fall back to legacy snapshots.yml if main config doesn't have snapshot presets
    legacy_cfg_path = Path(".xsarena/snapshots.yml")
    if legacy_cfg_path.exists():
        try:
            data = yaml.safe_load(legacy_cfg_path.read_text(encoding="utf-8")) or {}
            presets = data.get("presets") or {}
            default_excludes = data.get("default_excludes") or DEFAULT_EXCLUDES
            # normalize shapes
            norm = {}
            for name, spec in presets.items():
                inc = spec.get("include", []) or []
                exc = spec.get("exclude", []) or []
                norm[name.lower()] = {"include": list(inc), "exclude": list(exc)}
            return (norm if norm else DEFAULT_PRESETS, default_excludes)
        except Exception:
            pass

    return (DEFAULT_PRESETS, DEFAULT_EXCLUDES)
