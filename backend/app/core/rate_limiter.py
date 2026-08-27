import logging
import os

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger("rate-limiter")

# Tracks whether we are already in a known Redis outage (see __call__).
_redis_down = False


def client_ip(request: Request) -> str:
    """Best available client address.

    Behind a proxy, `request.client.host` is the proxy, which would put every user in
    one bucket. `TRUST_PROXY_HEADERS` gates the X-Forwarded-For fallback because a
    directly-exposed app would let clients forge it.
    """
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Redis-backed fixed-window rate limiter. Each limiter gets its own key
    namespace so a tight bucket and a loose one don't drain the same counter."""

    def __init__(self, requests_per_minute: int = 60, name: str = "default"):
        self.requests_per_minute = requests_per_minute
        self.name = name

    async def __call__(self, request: Request):
        # Bypass rate limits during automated testing to avoid test collisions.
        if "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "") or os.environ.get("TESTING") == "True":
            return

        global _redis_down

        try:
            redis = get_redis()
            key = f"rate_limit:{self.name}:{client_ip(request)}"

            count = await redis.incr(key)
            if _redis_down:
                _redis_down = False
                logger.info("Redis reachable again, rate limiting resumed")
            if count == 1:
                await redis.expire(key, 60)

            if count > self.requests_per_minute:
                ttl = await redis.ttl(key)
                logger.warning(
                    "Rate limit exceeded",
                    extra={"limiter": self.name, "count": count, "limit": self.requests_per_minute},
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please slow down and try again shortly.",
                    headers={"Retry-After": str(max(ttl, 1))},
                )
        except HTTPException:
            raise
        except Exception as e:
            # Fail open if Redis is down: auth and the token budget still apply.
            # Logged once per outage — this fires on every request, and a full
            # stack trace per request buries everything else in the log.
            if not _redis_down:
                _redis_down = True
                logger.warning(f"Redis unreachable, rate limiting disabled: {e}")


limit_60_per_min = RateLimiter(60, name="standard")
limit_10_per_min = RateLimiter(10, name="expensive")
# ponytail: per-IP only, so distributed credential stuffing gets through. Add
# per-account lockout or CAPTCHA if that shows up.
limit_auth = RateLimiter(10, name="auth")
