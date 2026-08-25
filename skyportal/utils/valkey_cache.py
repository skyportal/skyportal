"""Generic async key/value cache backed by Valkey.

This is a small, domain-agnostic caching layer for SkyPortal — distinct from the
disk-based ``Cache`` in :mod:`skyportal.utils.cache` (which stores cutout files
on disk). It provides a process-wide async client for short-lived,
network-shared cache entries (expensive-query memoization, broker-canonical
read-through caches, rate-limit counters, ...). Feature code builds its own
namespaced keys and TTLs on top of it.

Valkey speaks the redis protocol, so the Python ``redis.asyncio`` client talks to
it directly. Connection settings come from a ``redis:`` config block
(``host``/``port``/``db``); the client opens a single pooled async connection.

Design notes:
- The ``redis`` client is imported lazily and ``cfg`` is read lazily, so this
  module imports fine without the optional dependency, a running Valkey, or a
  loaded config.
- Every operation is best-effort: a connection error is logged and swallowed
  (returning a miss / no-op), so the cache can never take down a code path that
  uses it.
- When ``cache.enabled`` is false (the default), :func:`get_cache` returns a
  no-op cache so callers need no conditional logic.
"""

import json

from baselayer.log import make_log

log = make_log("valkey_cache")


class ValkeyCache:
    """Thin async wrapper over a pooled ``redis.asyncio`` client.

    All methods are best-effort: any error is logged and swallowed (returning a
    miss / no-op) so a Valkey outage degrades gracefully to the un-cached path.
    """

    def __init__(self, host="localhost", port=6379, db=0, default_ttl=300):
        self._url = f"redis://{host}:{port}/{db}"
        self._default_ttl = default_ttl
        self._client = None

    def _connect(self):
        # redis-py's async client maintains its own connection pool; create it
        # once and reuse it process-wide.
        if self._client is None:
            import redis.asyncio as redis  # lazy: optional dependency

            self._client = redis.from_url(
                self._url,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
        return self._client

    async def get(self, key):
        """Return the raw cached bytes for ``key``, or None on miss/error."""
        try:
            return await self._connect().get(key)
        except Exception as e:
            log(f"get failed [{key}]: {e}")
            return None

    async def set(self, key, value, ttl=None):
        """Set ``key`` to raw ``value`` with a TTL (seconds). Returns success."""
        try:
            await self._connect().set(key, value, ex=ttl or self._default_ttl)
            return True
        except Exception as e:
            log(f"set failed [{key}]: {e}")
            return False

    async def get_json(self, key):
        """Return the JSON-decoded cached value for ``key``, or None."""
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception as e:
            log(f"decode failed [{key}]: {e}")
            return None

    async def set_json(self, key, value, ttl=None):
        """JSON-encode ``value`` and cache it under ``key``."""
        try:
            payload = json.dumps(value, default=str)
        except Exception as e:
            log(f"encode failed [{key}]: {e}")
            return False
        return await self.set(key, payload, ttl=ttl)

    async def delete(self, key):
        """Delete a single key."""
        try:
            await self._connect().unlink(key)
            return True
        except Exception as e:
            log(f"delete failed [{key}]: {e}")
            return False

    async def delete_prefix(self, prefix):
        """Delete every key beginning with ``prefix``. Returns the count removed.

        Uses non-blocking ``SCAN`` + ``UNLINK`` so it never stalls the server
        the way ``KEYS`` would.
        """
        deleted = 0
        try:
            client = self._connect()
            async for key in client.scan_iter(match=f"{prefix}*", count=200):
                await client.unlink(key)
                deleted += 1
        except Exception as e:
            log(f"delete_prefix failed [{prefix}]: {e}")
        return deleted


class _NoOpCache:
    """Stand-in used when caching is disabled, so callers never branch."""

    async def get(self, key):
        return None

    async def set(self, key, value, ttl=None):
        return False

    async def get_json(self, key):
        return None

    async def set_json(self, key, value, ttl=None):
        return False

    async def delete(self, key):
        return False

    async def delete_prefix(self, prefix):
        return 0


_cache = None
_noop = _NoOpCache()


def get_cache():
    """Return the process-wide :class:`ValkeyCache`, or a no-op cache when
    disabled.

    Reads the ``redis:`` config block (``host``/``port``/``db``) plus
    ``cache.enabled`` and ``cache.ttl.default``. With ``cache.enabled``
    false (the default) this returns a no-op cache, so call sites need no
    conditional logic and behavior is unchanged until caching is turned on.
    """
    global _cache
    from baselayer.app.env import load_env

    _, cfg = load_env()
    if not cfg.get("cache.enabled", False):
        return _noop
    if _cache is None:
        _cache = ValkeyCache(
            host=cfg.get("redis.host", "localhost"),
            port=int(cfg.get("redis.port", 6379)),
            db=int(cfg.get("redis.db", 0) or 0),
            default_ttl=int(cfg.get("cache.ttl.default", 300)),
        )
    return _cache
