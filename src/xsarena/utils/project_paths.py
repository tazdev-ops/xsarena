"""Utility functions for robust project root resolution."""
import os
from pathlib import Path


def get_project_root() -> Path:
    """
    Get the project root directory using multiple strategies.

    The function looks for the project root using these strategies in order:
    1. Use XSARENA_PROJECT_ROOT environment variable if set
    2. Walk up from current working directory looking for pyproject.toml or directives/ directory
    3. Return current working directory as a last resort

    Returns:
        Path: The project root directory
    """
    # Check if XSARENA_PROJECT_ROOT environment variable is set
    env_root = os.getenv("XSARENA_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()

    # Walk up from current working directory looking for project markers
    current_path = Path.cwd().resolve()
    search_path = current_path

    while search_path.parent != search_path:  # Not at root of filesystem
        # Check if this directory contains pyproject.toml or directives/
        if (search_path / "pyproject.toml").exists() or (
            search_path / "directives"
        ).is_dir():
            return search_path
        search_path = search_path.parent

    # If no project markers found, return current working directory as fallback
    return current_path


def base_from_config_url(url: str) -> str:
    """
    Extract the base URL by stripping trailing /v1 if present.

    Args:
        url: The full URL that may end with /v1

    Returns:
        The base URL with /v1 stripped if present
    """
    return url.rstrip("/").rstrip("/v1")
