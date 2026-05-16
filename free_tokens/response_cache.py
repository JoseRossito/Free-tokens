import os
import diskcache


class ResponseCache:
    def __init__(self, cache_dir: str | None = None, ttl: int = 3600):
        self._ttl = ttl
        self._dir = cache_dir or os.path.join(os.path.expanduser("~"), ".free_tokens_cache")
        self._cache = diskcache.Cache(self._dir)
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> dict | None:
        value = self._cache.get(key)
        if value is not None:
            self._hits += 1
            return value
        self._misses += 1
        return None

    def set(self, key: str, response: dict) -> None:
        self._cache.set(key, response, expire=self._ttl)

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size_bytes": self._cache.volume(),
        }

    def close(self) -> None:
        self._cache.close()
