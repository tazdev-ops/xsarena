"""Cache module for XSArena - provides Redis and fallback caching for prompts/anchors."""

import hashlib
import os
from typing import Optional


class Cache:
    """Cache for storing LLM responses by input content to avoid repeated costs."""

    def __init__(self):
        self.redis_client = None
        self.use_redis = False
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection if available."""
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis

                self.redis_client = redis.from_url(redis_url)
                self.use_redis = True
            except ImportError:
                # Redis not available, use fallback
                pass
        else:
            # No Redis URL provided, use fallback
            pass

    def _generate_key(self, system_text: str, user_text: str, anchor_digest: str, model: str) -> str:
        """Generate a cache key from the input components."""
        key_content = f"{system_text}||{user_text}||{anchor_digest}||{model}"
        return hashlib.sha1(key_content.encode("utf-8")).hexdigest()

    def get(self, system_text: str, user_text: str, anchor_digest: str, model: str) -> Optional[str]:
        """Get a cached response if available."""
        key = self._generate_key(system_text, user_text, anchor_digest, model)

        if self.use_redis and self.redis_client:
            try:
                cached = self.redis_client.get(key)
                if cached:
                    return cached.decode("utf-8")
            except Exception:
                # If Redis fails, continue to fallback
                pass

        # Fallback to local file cache
        try:
            import json

            cache_dir = os.path.join(".xsarena", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"{key[:10]}.json")

            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    return cached_data.get("response")
        except Exception:
            pass

        return None

    def set(
        self, system_text: str, user_text: str, anchor_digest: str, model: str, response: str, ttl: int = 86400
    ) -> bool:
        """Set a cached response."""
        key = self._generate_key(system_text, user_text, anchor_digest, model)

        # Store in Redis if available
        redis_ok = False
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(key, ttl, response)
                redis_ok = True
            except Exception:
                redis_ok = False

        # Also store in local file as fallback
        try:
            import json

            cache_dir = os.path.join(".xsarena", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"{key[:10]}.json")

            cache_data = {
                "system_text": system_text,
                "user_text": user_text,
                "anchor_digest": anchor_digest,
                "model": model,
                "response": response,
                "ttl": ttl,
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
        except Exception:
            pass

        return redis_ok  # Return success status based on Redis

    def hit(self, system_text: str, user_text: str, anchor_digest: str, model: str) -> bool:
        """Check if a key exists in cache."""
        return self.get(system_text, user_text, anchor_digest, model) is not None


# Global cache instance
_cache = None


def get_cache() -> Cache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
