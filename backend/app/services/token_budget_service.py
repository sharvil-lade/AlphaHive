import logging
from typing import Optional
from redis.asyncio import Redis

from backend.app.core.config import settings

logger = logging.getLogger("token-budget-service")


class TokenBudgetService:
    """Service to track and cap LLM token budgets per user session to prevent budget exhaustion."""

    def __init__(self, max_tokens_per_session: int = 100000):
        self.max_tokens_per_session = max_tokens_per_session
        self.redis: Optional[Redis] = None

    async def _get_redis(self) -> Redis:
        if self.redis is None:
            self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis

    async def get_usage(self, session_id: str) -> int:
        """Get the current accumulated token usage for a session."""
        try:
            redis = await self._get_redis()
            key = f"token_budget:{session_id}"
            val = await redis.get(key)
            return int(val) if val else 0
        except Exception as e:
            logger.error(f"Failed to fetch token usage: {e}")
            return 0

    async def check_budget(self, session_id: str, required_tokens: int = 2000) -> bool:
        """Check if a session has enough remaining token budget to run a request."""
        try:
            usage = await self.get_usage(session_id)
            if usage + required_tokens > self.max_tokens_per_session:
                logger.warning(f"Session {session_id} has exceeded token budget ({usage}/{self.max_tokens_per_session})")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to check token budget: {e}")
            return True # fail open to prevent blocking execution if Redis fails

    async def track_usage(self, session_id: str, tokens_used: int):
        """Track and increment token usage for a session."""
        try:
            redis = await self._get_redis()
            key = f"token_budget:{session_id}"
            await redis.incrby(key, tokens_used)
            # Set usage key to expire in 24 hours (86400 seconds)
            await redis.expire(key, 86400)
            logger.info(f"Session {session_id} consumed {tokens_used} tokens. Total: {await redis.get(key)}/{self.max_tokens_per_session}")
        except Exception as e:
            logger.error(f"Failed to track token usage: {e}")
            pass


token_budget_service = TokenBudgetService(max_tokens_per_session=settings.MAX_TOKENS_PER_SESSION)
