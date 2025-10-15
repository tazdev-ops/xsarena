from __future__ import annotations
from pathlib import Path
import yaml
from .specs import DEFAULT_PROFILES

def load_profiles() -> dict:
    p = Path("directives/profiles/presets.yml")
    if p.exists():
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return {**DEFAULT_PROFILES, **(data.get("profiles") or {})}
        except Exception:
            return DEFAULT_PROFILES
    return DEFAULT_PROFILES