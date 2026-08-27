import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from conftest import requires_redis
from fastapi import HTTPException
from httpx import AsyncClient

from app.core.config import settings
from app.core.logging_config import JSONFormatter, configure_logging
from app.core.rate_limiter import RateLimiter
from app.main import app
from app.services.token_budget_service import TokenBudgetService


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_metrics_endpoint(client):
    """Test that the custom Prometheus metrics endpoint is online and formats correctly."""
    # Trigger a request first to populate metrics
    await client.get("/api/v1/health")

    resp = await client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "# HELP http_requests_total" in text
    assert "# TYPE http_requests_total" in text


async def test_rate_limiter_unit(monkeypatch):
    """Unit test the RateLimiter logic directly using mock Redis."""
    # Temporarily clear testing environment bypasses for the limiter unit test
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    limiter = RateLimiter(requests_per_minute=5, name="unit")

    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 6  # 6th request in the window, limit is 5
    mock_redis.ttl.return_value = 42
    monkeypatch.setattr("app.core.rate_limiter.get_redis", lambda: mock_redis)

    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.client.host = "1.2.3.4"

    with pytest.raises(HTTPException) as exc_info:
        await limiter(mock_request)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "42"


async def test_rate_limiter_buckets_are_namespaced_per_limiter():
    """Two limiters must not drain the same counter, or the tightest limit silently
    applies to every endpoint."""
    from app.core.rate_limiter import limit_10_per_min, limit_60_per_min

    assert limit_10_per_min.name != limit_60_per_min.name


async def test_rate_limiter_prefers_the_forwarded_client_ip(monkeypatch):
    """Behind a proxy, every user would otherwise share one bucket."""
    from app.core.rate_limiter import client_ip

    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    request = MagicMock()
    request.headers = {"x-forwarded-for": "203.0.113.9, 10.0.0.1"}
    request.client.host = "10.0.0.1"
    assert client_ip(request) == "203.0.113.9"


@requires_redis
async def test_token_budget_tracking():
    """Test token budget service counting and threshold checks."""
    import uuid

    session_id = f"test_budget_session_{uuid.uuid4().hex}"

    # Initialize a custom budget tracker with 500 max tokens for testing
    budget_service = TokenBudgetService(max_tokens_per_session=500)

    # 1. Initial usage is 0
    assert await budget_service.get_usage(session_id) == 0

    # 2. Check budget passes
    assert await budget_service.check_budget(session_id, required_tokens=100) is True

    # 3. Track usage increments budget
    await budget_service.track_usage(session_id, tokens_used=300)
    assert await budget_service.get_usage(session_id) == 300

    # 4. Check budget with threshold near limit passes
    assert await budget_service.check_budget(session_id, required_tokens=150) is True

    # 5. Check budget with threshold exceeding limit fails
    assert await budget_service.check_budget(session_id, required_tokens=250) is False


def test_json_formatter_output():
    """Test that JSONFormatter produces parseable JSON with required fields."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test-logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Hello production logging",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test-logger"
    assert parsed["message"] == "Hello production logging"
    assert parsed["line"] == 42
    assert "timestamp" in parsed
    # Timestamp should be a valid UTC ISO 8601 string ending in Z
    assert parsed["timestamp"].endswith("Z")


def test_configure_logging_does_not_raise():
    """Test that configure_logging() runs without errors in both modes."""
    # JSON mode
    configure_logging(level="INFO", json_output=True)
    # Human-readable mode
    configure_logging(level="DEBUG", json_output=False)
    # Restore to a clean state
    configure_logging(level="INFO", json_output=False)


def test_settings_cors_origins_wildcard():
    """Test that CORS origin parsing returns ['*'] for wildcard default."""
    origins = settings.get_cors_origins()
    assert isinstance(origins, list)
    assert len(origins) >= 1


def test_settings_max_tokens_per_session():
    """Test that MAX_TOKENS_PER_SESSION is a positive integer from config."""
    assert settings.MAX_TOKENS_PER_SESSION > 0
    assert isinstance(settings.MAX_TOKENS_PER_SESSION, int)


async def test_health_endpoint_structure(client):
    """Test health check endpoint returns expected JSON structure."""
    resp = await client.get("/api/v1/health")
    data = resp.json()
    if resp.status_code == 200:
        assert "status" in data
        assert "environment" in data
        assert data["status"] == "healthy"
    else:
        # Unhealthy but structured error response
        assert "detail" in data


def test_shared_redis_client_has_timeouts():
    """The shared client must bound how long a Redis outage can block a request.

    redis-py waits forever by default. Without these, an unreachable Redis turned
    every guarded endpoint into a hang: one chat POST stacked two rate-limiter checks,
    a liveness ping and a budget lookup, and never answered at all.
    """
    from app.core.redis import CONNECT_TIMEOUT, OPERATION_TIMEOUT, get_redis

    kwargs = get_redis().connection_pool.connection_kwargs
    assert kwargs["socket_connect_timeout"] == CONNECT_TIMEOUT
    assert kwargs["socket_timeout"] == OPERATION_TIMEOUT
    assert CONNECT_TIMEOUT <= 2 and OPERATION_TIMEOUT <= 5


async def test_redis_available_fails_fast_when_down(monkeypatch):
    """An unreachable Redis reports unavailable quickly, rather than hanging."""
    import time

    import app.core.redis as redis_module

    monkeypatch.setattr(redis_module, "_client", None)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://127.0.0.1:6390/0")  # nothing listens here
    try:
        started = time.monotonic()
        assert await redis_module.redis_available() is False
        assert time.monotonic() - started < redis_module.CONNECT_TIMEOUT + 2
    finally:
        await redis_module.close_redis()
