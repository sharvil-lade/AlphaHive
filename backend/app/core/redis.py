"""The one Redis client for the whole app.

Every Redis use here is meant to degrade gracefully — caches and rate limiting fail
open, chat fails fast with a 503 — and all of that depends on failure being *bounded*.
redis-py waits forever by default, so an unreachable Redis turned each guarded call
into a hang rather than an error: a single chat POST stacked two rate-limiter checks,
a liveness probe and a budget check, and took ~16s to answer instead of ~0.

One shared client also means one connection pool, instead of a separate pool per
service module reconnecting independently.
"""

import logging

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger("redis")

# Deliberately short. Redis is either local or same-datacentre; anything slower than
# this is an outage, and every caller has a fallback that beats making the user wait.
CONNECT_TIMEOUT = 1.0
OPERATION_TIMEOUT = 2.0

_client: Redis | None = None


def get_redis() -> Redis:
    """The shared client. Cheap to call — the connection is made lazily, per command."""
    global _client
    if _client is None:
        _client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=CONNECT_TIMEOUT,
            socket_timeout=OPERATION_TIMEOUT,
            # A retry would double every timeout above; callers already fall back.
            retry_on_timeout=False,
            health_check_interval=30,
        )
    return _client


async def redis_available() -> bool:
    """True if Redis answers a ping within the timeouts above.

    Chat streaming reads and writes exclusively through Redis, so without it a run
    starts, produces nothing, and the client spins forever. Callers use this to fail
    fast with a real error instead.
    """
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


async def close_redis() -> None:
    """Release the pool on shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
