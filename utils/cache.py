from __future__ import annotations

import time
from typing import Any, Dict, Tuple


class TTLCache:
    """Simple in-memory TTL cache with stale indication."""

    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._store: Dict[str, Tuple[Any, float]] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.time() + self.ttl)

    def get(self, key: str) -> Tuple[Any, bool]:
        """
        Returns (value, stale).
        If missing, returns (None, False).
        If expired, returns (value, True) so callers can decide to use stale data.
        """
        item = self._store.get(key)
        if not item:
            return None, False
        value, expires_at = item
        now = time.time()
        if now > expires_at:
            return value, True
        return value, False

    def clear(self) -> None:
        self._store.clear()

