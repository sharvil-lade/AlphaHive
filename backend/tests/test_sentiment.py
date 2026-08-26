import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.main import app
from app.services.sentiment_service import sentiment_service

# Use pytest-asyncio to handle async tests
from conftest import requires_redis

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@requires_redis
async def test_sentiment_summary_endpoint(client):
    """Test sentiment/summary endpoint, verifying sentiment scoring and structured response formats."""
    # Query Apple sentiment
    resp = await client.get("/api/v1/sentiment/summary?symbol=AAPL")
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "AAPL"
    assert "score" in data
    assert "rating" in data
    assert "summary" in data
    assert "opportunities" in data
    assert "threats" in data
    assert "source" in data

    # Verify score boundary constraints
    assert -100 <= data["score"] <= 100
    assert data["rating"] in ["BUY", "HOLD", "SELL"]
    assert isinstance(data["opportunities"], list)
    assert isinstance(data["threats"], list)


async def test_local_sentiment_fallback_is_not_symbol_biased():
    """The deterministic local fallback must never special-case a symbol.

    Regression test for a removed anti-pattern where NVDA was hardcoded to a forced
    bullish floor (score >= 50, rating BUY) and TSLA to a forced bearish ceiling
    (score <= -30, rating SELL) regardless of the actual input text. Tested directly
    against `_evaluate_local_sentiment` (bypassing the LLM) so it's deterministic
    and independent of whether an LLM provider is configured.
    """
    identical_text = "quarterly results were roughly in line with expectations"

    nvda_result = sentiment_service._evaluate_local_sentiment("NVDA", [], [], identical_text)
    tsla_result = sentiment_service._evaluate_local_sentiment("TSLA", [], [], identical_text)
    generic_result = sentiment_service._evaluate_local_sentiment("XYZ", [], [], identical_text)

    # Same input text must yield the same score/rating regardless of symbol —
    # any divergence would mean symbol-specific logic has crept back in.
    assert nvda_result["score"] == tsla_result["score"] == generic_result["score"]
    assert nvda_result["rating"] == tsla_result["rating"] == generic_result["rating"]
    assert nvda_result["source"] == "local_lexical_fallback"
