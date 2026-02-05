"""TTL cache helpers for secrets fetched from A8N Identity."""

from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
from importlib import import_module
from typing import Generic, TypeVar, cast

T = TypeVar("T")


class CacheManager(Generic[T]):
    """Thin async-friendly wrapper around ``cachetools.TTLCache``."""

    def __init__(self, maxsize: int, ttl_seconds: int) -> None:
        try:
            ttl_cache_cls = getattr(import_module("cachetools"), "TTLCache")
        except ModuleNotFoundError as exc:  # pragma: no cover - defensive
            raise RuntimeError("cachetools must be installed to enable secrets caching") from exc

        self._cache: MutableMapping[str, T] = cast(
            MutableMapping[str, T], ttl_cache_cls(maxsize=maxsize, ttl=ttl_seconds)
        )
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> T | None:
        """Return a cached value if it exists and is still valid."""

        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: T) -> None:
        """Store a value in the cache."""

        async with self._lock:
            self._cache[key] = value

    async def clear(self) -> None:
        """Remove all cached entries."""

        async with self._lock:
            self._cache.clear()
