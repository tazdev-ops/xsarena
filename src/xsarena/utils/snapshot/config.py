"""
Configuration handling for XSArena snapshot utility.
"""

from pathlib import Path
from typing import Dict

try:
    import tomllib  # Python 3.11+
except ImportError:
    tomllib = None

ROOT = Path.cwd()


def read_snapshot_config() -> Dict:
    """
    Read snapshot configuration from .snapshot.toml with fallbacks.
    """
    cfg = {
        "mode": "standard",
        "max_size": 262144,  # 256KB
        "redact": True,
        "context": {"git": True, "jobs": True, "manifest": True},
        "modes": {
            "minimal": {
                "include": [
                    ".snapshot.toml",
                    "README.md",
                    "COMMANDS_REFERENCE.md",
                    "pyproject.toml",
                    "src/xsarena/**",
                ],
                "exclude": [
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
                ],
            },
            "standard": {
                "include": [
                    ".snapshot.toml",
                    "README.md",
                    "COMMANDS_REFERENCE.md",
                    "pyproject.toml",
                    "src/xsarena/**",
                    "docs/**",
                    "data/schemas/**",
                    "directives/manifest.yml",
                    "directives/profiles/presets.yml",
                    "directives/modes.catalog.json",
                ],
                "exclude": [
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
                    # Explicitly omit non-architectural or generated content
                    "books/**",
                    "review/**",
                    "recipes/**",
                    "tests/**",
                    "packaging/**",
                    "pipelines/**",
                    "examples/**",
                    "directives/_preview/**",
                    "directives/_mixer/**",
                    "directives/quickref/**",
                    "directives/roles/**",
                    "directives/prompt/**",
                    "directives/style/**",
                ],
            },
            "full": {
                "include": [
                    "README.md",
                    "COMMANDS_REFERENCE.md",
                    "pyproject.toml",
                    "src/**",
                    "docs/**",
                    "directives/**",
                    "data/**",
                    "recipes/**",
                    "tests/**",
                    "tools/**",
                    "scripts/**",
                    "books/**",
                    "packaging/**",
                    "pipelines/**",
                    "examples/**",
                    "review/**",
                ],
                "exclude": [
                    ".git/**",
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
                    "*.egg-info/**",
                    ".ipynb_checkpoints/**",
                ],
            },
        },
    }

    # Try to read .snapshot.toml
    config_path = ROOT / ".snapshot.toml"
    if config_path.exists() and tomllib:
        try:
            data = tomllib.loads(config_path.read_text(encoding="utf-8"))
            # Update modes separately since it's a nested structure
            if "modes" in data:
                cfg["modes"].update(data.pop("modes", {}))
            cfg.update({k: v for k, v in data.items() if k in cfg or k == "context"})
        except Exception:
            # If .snapshot.toml is invalid, use defaults
            pass

    return cfg
