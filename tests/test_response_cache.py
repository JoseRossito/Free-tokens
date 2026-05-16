import tempfile
import os
from free_tokens.response_cache import ResponseCache


def _make_cache():
    tmpdir = tempfile.mkdtemp()
    return ResponseCache(cache_dir=tmpdir, ttl=60)


def test_miss_returns_none():
    cache = _make_cache()
    assert cache.get("nonexistent") is None


def test_set_and_get():
    cache = _make_cache()
    cache.set("key1", {"text": "hello", "input_tokens": 10, "output_tokens": 5})
    result = cache.get("key1")
    assert result is not None
    assert result["text"] == "hello"


def test_stats_tracks_hits_misses():
    cache = _make_cache()
    cache.get("missing")
    cache.set("k", {"text": "x"})
    cache.get("k")
    cache.get("k")
    stats = cache.stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1


def test_clear():
    cache = _make_cache()
    cache.set("k", {"text": "x"})
    cache.clear()
    assert cache.get("k") is None
