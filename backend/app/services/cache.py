"""Thin Redis cache wrapper with graceful degradation.

If Redis is unavailable the app still works — cache operations become no-ops.
Never let caching failures break a request.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

try:
    import redis

    _client: "redis.Redis | None" = redis.from_url(
        settings.redis_url, decode_responses=True, socket_connect_timeout=1
    )
except Exception as exc:  # noqa: BLE001
    logger.warning("Redis unavailable, caching disabled: %s", exc)
    _client = None


def cache_get(key: str) -> Any | None:
    if _client is None:
        return None
    try:
        raw = _client.get(key)
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    if _client is None:
        return
    try:
        _client.setex(key, ttl or settings.cache_ttl_seconds, json.dumps(value))
    except Exception:  # noqa: BLE001
        pass


def cache_clear(prefix: str = "tar:") -> None:
    if _client is None:
        return
    try:
        for k in _client.scan_iter(match=f"{prefix}*"):
            _client.delete(k)
    except Exception:  # noqa: BLE001
        pass
