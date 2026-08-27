import json
import logging
from datetime import datetime
from typing import Any

from app.core.redis import get_redis, redis_available

__all__ = ["get_redis", "redis_available", "log_agent_activity", "emit_chat_event"]

logger = logging.getLogger("agent-utils")


async def log_agent_activity(
    run_id: str,
    node: str,
    message: str,
) -> dict[str, Any]:
    """Helper to log activity both into Redis for streaming and return the state log dict."""
    log_entry = {"node": node, "message": message, "timestamp": datetime.utcnow().isoformat()}

    try:
        redis = get_redis()
        cache_key = f"agent_run_logs:{run_id}"
        await redis.rpush(cache_key, json.dumps(log_entry))
        await redis.expire(cache_key, 86400)
    except Exception as e:
        logger.error(f"Failed to log activity to Redis for run {run_id}: {e}")

    return log_entry


async def emit_chat_event(message_id: str, event: dict[str, Any]) -> None:
    """Push a chat-stream event (agent-status update or text delta) to Redis, read
    by the SSE endpoint at GET /api/v1/chat/messages/{message_id}/stream."""
    try:
        redis = get_redis()
        cache_key = f"chat_events:{message_id}"
        await redis.rpush(cache_key, json.dumps(event))
        await redis.expire(cache_key, 86400)
    except Exception as e:
        logger.error(f"Failed to emit chat event to Redis for message {message_id}: {e}")
