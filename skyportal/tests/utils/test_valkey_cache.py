"""Unit tests for the generic async Valkey cache (skyportal.utils.valkey_cache).

These run without a Valkey server: the no-op / disabled paths and the
URL construction need nothing, the wrapper logic (JSON round-trip, prefix
deletion) is exercised against a tiny in-memory fake client, and graceful
degradation is verified against an unreachable port.
"""

import asyncio
import fnmatch

from skyportal.utils.valkey_cache import (
    ValkeyCache,
    _NoOpCache,
    get_cache,
)


def _run(coro):
    return asyncio.run(coro)


class _FakeRedis:
    """Minimal async stand-in for redis.asyncio, backed by a dict, exposing just
    the methods ValkeyCache uses (get/set/unlink/scan_iter)."""

    def __init__(self):
        self.store = {}
        self.expirations = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        self.expirations[key] = ex
        return True

    async def unlink(self, key):
        self.store.pop(key, None)
        self.expirations.pop(key, None)
        return 1

    async def scan_iter(self, match=None, count=None):
        # redis glob matching ("prefix*"); iterate a snapshot since we mutate.
        for key in list(self.store):
            if match is None or fnmatch.fnmatch(key, match):
                yield key


def test_noop_cache_methods():
    """A disabled/no-op cache answers every operation as a miss, never raising."""
    cache = _NoOpCache()
    assert _run(cache.get("k")) is None
    assert _run(cache.get_json("k")) is None
    assert _run(cache.set("k", "v")) is False
    assert _run(cache.set_json("k", {"a": 1})) is False
    assert _run(cache.delete("k")) is False
    assert _run(cache.delete_prefix("p:")) == 0


def test_get_cache_disabled_returns_noop():
    """With cache.enabled false (the default), get_cache returns a no-op cache so
    callers need no conditional logic and behavior is unchanged."""
    cache = get_cache()
    assert isinstance(cache, _NoOpCache)


def test_url_construction_and_lazy_connect():
    """ValkeyCache builds the redis://host:port/db URI and does not open a
    connection until first use."""
    cache = ValkeyCache(host="example", port=1234, db=2, default_ttl=42)
    assert cache._url == "redis://example:1234/2"
    assert cache._client is None  # lazy: no connection at construction


def test_json_roundtrip_with_fake_client():
    """set_json encodes and get_json decodes the same value."""
    cache = ValkeyCache(default_ttl=99)
    cache._client = _FakeRedis()

    value = {"obj_id": "ZTF1", "points": [1, 2, 3], "nested": {"x": True}}
    assert _run(cache.set_json("photcache:v1:ZTF1:scope:variant", value)) is True
    assert _run(cache.get_json("photcache:v1:ZTF1:scope:variant")) == value
    # Default TTL is applied when none is supplied.
    assert cache._client.expirations["photcache:v1:ZTF1:scope:variant"] == 99


def test_get_json_miss_returns_none():
    cache = ValkeyCache()
    cache._client = _FakeRedis()
    assert _run(cache.get_json("absent")) is None


def test_explicit_ttl_overrides_default():
    cache = ValkeyCache(default_ttl=99)
    cache._client = _FakeRedis()
    _run(cache.set("k", "v", ttl=5))
    assert cache._client.expirations["k"] == 5


def test_delete_and_delete_prefix():
    """delete removes one key; delete_prefix removes only the matching prefix and
    reports the count, leaving other objects' entries intact."""
    cache = ValkeyCache()
    cache._client = _FakeRedis()
    _run(cache.set("photcache:v1:ZTF1:s1:v1", "a"))
    _run(cache.set("photcache:v1:ZTF1:s2:v1", "b"))
    _run(cache.set("photcache:v1:ZTF2:s1:v1", "c"))  # different object

    assert _run(cache.delete("photcache:v1:ZTF1:s1:v1")) is True
    assert _run(cache.get("photcache:v1:ZTF1:s1:v1")) is None

    removed = _run(cache.delete_prefix("photcache:v1:ZTF1:"))
    assert removed == 1  # only the remaining ZTF1 entry
    assert _run(cache.get("photcache:v1:ZTF1:s2:v1")) is None
    # The other object's entry is untouched.
    assert _run(cache.get("photcache:v1:ZTF2:s1:v1")) == "c"


def test_graceful_degradation_when_unreachable():
    """A real client pointed at a closed port must degrade to misses/no-ops
    (log and carry on), never propagating an exception to the caller."""
    # Port 6: a reserved, unused port -> connection refused fast.
    cache = ValkeyCache(host="127.0.0.1", port=6)
    assert _run(cache.get("k")) is None
    assert _run(cache.get_json("k")) is None
    assert _run(cache.set("k", "v")) is False
    assert _run(cache.set_json("k", {"a": 1})) is False
    assert _run(cache.delete("k")) is False
    assert _run(cache.delete_prefix("p:")) == 0
