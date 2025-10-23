from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_MANIFEST_CACHE: Optional[Dict[str, Any]] = None
MANIFEST_PATH = Path("directives/manifest.yml")


@lru_cache(maxsize=1)
def _load_manifest_internal() -> Dict[str, Any]:
    """Internal function to load manifest with caching."""
    empty = {"roles": [], "prompts": [], "overlays": [], "profiles": {}}
    if not MANIFEST_PATH.exists():
        return empty
    try:
        data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
        for key in ["roles", "prompts", "overlays"]:
            if key not in data or not isinstance(data[key], list):
                data[key] = []
        return data
    except Exception:
        return empty


def load_manifest(force_refresh: bool = False) -> Dict[str, Any]:
    """Load manifest with caching optimization."""
    global _MANIFEST_CACHE
    if force_refresh:
        # Clear the cached version when force_refresh is True
        _load_manifest_internal.cache_clear()
        _MANIFEST_CACHE = None

    if _MANIFEST_CACHE is not None and not force_refresh:
        return _MANIFEST_CACHE

    # Load the manifest using the cached function
    result = _load_manifest_internal()

    # Update the global cache for backward compatibility
    if _MANIFEST_CACHE is None:
        _MANIFEST_CACHE = result

    return result


def get_role(name: str) -> Optional[Dict[str, Any]]:
    man = load_manifest()
    for r in man.get("roles", []):
        if r.get("name") == name:
            return r
    return None
