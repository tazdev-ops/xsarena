"""Prompt composition cache for XSArena."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.prompt import compose_prompt


class PromptCache:
    """Cache for prompt compositions to avoid recomputation."""

    def __init__(self, cache_dir: str = ".xsarena/tmp"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "prompt_cache.json"
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                content = self.cache_file.read_text(encoding="utf-8")
                return json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {}
        return {}

    def _save_cache(self):
        """Save cache to file."""
        try:
            self.cache_file.write_text(
                json.dumps(self._cache, indent=2), encoding="utf-8"
            )
        except Exception:
            # If we can't save the cache, just continue
            pass

    def _generate_key(
        self,
        subject: str,
        overlays: list,
        extra_notes: str,
        min_chars: int,
        passes: int,
        max_chunks: int,
        apply_reading_overlay: bool = False,
    ) -> str:
        """Generate a cache key from prompt parameters."""
        key_data = {
            "subject": subject,
            "overlays": sorted(overlays) if overlays else [],
            "extra_notes": extra_notes or "",
            "min_chars": min_chars,
            "passes": passes,
            "max_chunks": max_chunks,
            "apply_reading_overlay": apply_reading_overlay,
        }
        # Create a hash of the key data
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]  # Short hash

    def get_cached(
        self,
        subject: str,
        overlays: list,
        extra_notes: str,
        min_chars: int,
        passes: int,
        max_chunks: int,
        apply_reading_overlay: bool = False,
    ) -> Optional[str]:
        """Get cached system text if available."""
        key = self._generate_key(
            subject,
            overlays,
            extra_notes,
            min_chars,
            passes,
            max_chunks,
            apply_reading_overlay,
        )
        if key in self._cache:
            # Log cache hit
            print(f"cache_hit: {key}")  # This will be captured by logging
            return self._cache[key].get("system_text")
        print(f"cache_miss: {key}")  # This will be captured by logging
        return None

    def cache_result(
        self,
        subject: str,
        overlays: list,
        extra_notes: str,
        min_chars: int,
        passes: int,
        max_chunks: int,
        system_text: str,
        apply_reading_overlay: bool = False,
    ):
        """Cache a prompt composition result."""
        key = self._generate_key(
            subject,
            overlays,
            extra_notes,
            min_chars,
            passes,
            max_chunks,
            apply_reading_overlay,
        )
        self._cache[key] = {
            "system_text": system_text,
            "subject": subject,
            "overlays": sorted(overlays) if overlays else [],
            "extra_notes": extra_notes or "",
            "min_chars": min_chars,
            "passes": passes,
            "max_chunks": max_chunks,
            "apply_reading_overlay": apply_reading_overlay,
        }
        self._save_cache()

    def clear(self):
        """Clear the cache."""
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "entries": len(self._cache),
            "file_size": (
                self.cache_file.stat().st_size if self.cache_file.exists() else 0
            ),
        }


# Global instance for convenience
prompt_cache = PromptCache()


def get_cached_composition(
    subject: str,
    base: str = "zero2hero",
    overlays: Optional[list] = None,
    extra_notes: Optional[str] = None,
    min_chars: int = 4200,
    passes: int = 1,
    max_chunks: int = 12,
    apply_reading_overlay: bool = False,
):
    """Get a cached prompt composition or compute and cache it."""
    if overlays is None:
        overlays = []

    # Try to get from cache first
    cached_result = prompt_cache.get_cached(
        subject,
        overlays,
        extra_notes or "",
        min_chars,
        passes,
        max_chunks,
        apply_reading_overlay,
    )

    if cached_result is not None:
        # Return a mock PromptComposition object with cached result
        from ..core.prompt import PromptComposition

        return PromptComposition(
            system_text=cached_result,
            applied={
                "subject": subject,
                "base": base,
                "overlays": overlays,
                "extra_notes": extra_notes,
                "continuation": {
                    "mode": "anchor",
                    "min_chars": min_chars,
                    "passes": passes,
                    "max_chunks": max_chunks,
                    "repeat_warn": True,
                },
            },
            warnings=[],
        )

    # If not in cache, compute the composition
    result = compose_prompt(
        subject=subject,
        base=base,
        overlays=overlays,
        extra_notes=extra_notes,
        min_chars=min_chars,
        passes=passes,
        max_chunks=max_chunks,
        apply_reading_overlay=apply_reading_overlay,
    )

    # Cache the result
    prompt_cache.cache_result(
        subject,
        overlays,
        extra_notes or "",
        min_chars,
        passes,
        max_chunks,
        result.system_text,
        apply_reading_overlay,
    )

    return result
