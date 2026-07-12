import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger("rate-limiter")


class RateLimiter:
    """Redis-backed API rate limiter to protect endpoints from abuse."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.redis: Optional[Redis] = None

    async def _get_redis(self) -> Redis:
        if self.redis is None:
            self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis

    async def __call__(self, request: Request):
        # Bypass rate limits during automated testing to avoid test collisions
        import os
        if "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "") or os.environ.get("TESTING") == "True":
            return

        try:
            redis = await self._get_redis()
            
            # Extract client IP address
            client_ip = request.client.host if request.client else "unknown"
            key = f"rate_limit:{client_ip}"
            
            # Atomic increment
            count = await redis.incr(key)
            if count == 1:
                # Set 60-second window expiration
                await redis.expire(key, 60)
                
            if count > self.requests_per_minute:
                logger.warning(f"Rate limit exceeded for client: {client_ip} ({count}/{self.requests_per_minute} req/min)")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again in a minute."
                )
        except HTTPException as he:
            raise he
        except Exception as e:
            # Resiliency: fail open if Redis is down/unreachable
            logger.error(f"Rate limiter encountered error, failing open: {e}")
            pass


# Instantiated dependencies
limit_60_per_min = RateLimiter(requests_per_minute=60)
limit_10_per_min = RateLimiter(requests_per_minute=10)
