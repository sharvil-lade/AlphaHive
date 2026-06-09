import pytest
import pytest_asyncio
from httpx import AsyncClient

from backend.app.main import app

# Use pytest-asyncio to handle async tests
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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


async def test_sentiment_summary_nvda_specifics(client):
    """Test NVDA specific sentiment response mapping details (mock fallbacks or OpenAI)."""
    resp = await client.get("/api/v1/sentiment/summary?symbol=NVDA")
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "NVDA"
    assert data["rating"] == "BUY"
    assert data["score"] >= 50
    assert len(data["opportunities"]) >= 2
    assert len(data["threats"]) >= 1
