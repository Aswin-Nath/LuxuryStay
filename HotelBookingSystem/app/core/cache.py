import json
from typing import Any, Optional
from app.core.redis_manager import redis


async def get_cached(key: str) -> Optional[Any]:
    if not redis:
        return None
    try:
        data = await redis.get(key)
        if data is None:
            return None
        return json.loads(data)
    except Exception:
        # swallowing redis errors to keep app functional
        return None


async def set_cached(key: str, value: Any, ttl: int = 300) -> None:
    if not redis:
        return
    try:
        await redis.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        return


async def invalidate_pattern(pattern: str) -> None:
    """Invalidate keys matching pattern (supports '*' wildcards)."""
    if not redis:
        return
    try:
        # Use scan_iter to avoid blocking
        keys = []
        async for k in redis.scan_iter(match=pattern):
            keys.append(k)
        if keys:
            await redis.delete(*keys)
    except Exception:
        return
