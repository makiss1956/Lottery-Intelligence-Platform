"""
Simple in-memory cache with TTL for analytics results.
"""

import time
from typing import Any, Dict, Optional

from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger("Cache")


class Cache:
    """Thread-unsafe simple cache. Sufficient for single-user CLI tool."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self.config = get_config()
        self.default_ttl = self.config.cache_ttl * 60  # seconds

    def get(self, key: str) -> Optional[Any]:
        """Return cached value if not expired."""
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() > entry["expires"]:
            del self._store[key]
            return None
        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value with TTL in seconds."""
        ttl = ttl or self.default_ttl
        self._store[key] = {
            "value": value,
            "expires": time.time() + ttl,
        }
        logger.debug(f"Cache set: {key} (TTL={ttl}s)")

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# Global instance
_cache_instance: Optional[Cache] = None


def get_cache() -> Cache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = Cache()
    return _cache_instance
