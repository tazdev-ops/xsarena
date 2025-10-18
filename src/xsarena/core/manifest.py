from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_MANIFEST_CACHE: Optional[Dict[str, Any]] = None
MANIFEST_PATH = Path("directives/manifest.yml")


def load_manifest(force_refresh: bool = False) -> Dict[str, Any]:
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None and not force_refresh:
        return _MANIFEST_CACHE
    empty = {"roles": [], "prompts": [], "overlays": [], "profiles": {}}
    if not MANIFEST_PATH.exists():
        _MANIFEST_CACHE = empty
        return _MANIFEST_CACHE
    try:
        data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
        for key in ["roles", "prompts", "overlays"]:
            if key not in data or not isinstance(data[key], list):
                data[key] = []
        _MANIFEST_CACHE = data
    except Exception:
        _MANIFEST_CACHE = empty
    return _MANIFEST_CACHE


def get_role(name: str) -> Optional[Dict[str, Any]]:
    man = load_manifest()
    for r in man.get("roles", []):
        if r.get("name") == name:
            return r
    return None
