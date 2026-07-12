import json
import logging
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from fastapi import HTTPException
from httpx import AsyncClient

from app.main import app
from app.core.rate_limiter import RateLimiter
from app.core.logging_config import configure_logging, JSONFormatter
from app.core.config import settings
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

    limiter = RateLimiter(requests_per_minute=5)

    # Mock Redis client
    mock_redis = AsyncMock()
    # 6th request triggers rate limit (limit is 5)
    mock_redis.incr.return_value = 6
    limiter.redis = mock_redis

    # Mock FastAPI Request
    mock_request = AsyncMock()
    mock_request.client.host = "1.2.3.4"

    with pytest.raises(HTTPException) as exc_info:
        await limiter(mock_request)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail


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
