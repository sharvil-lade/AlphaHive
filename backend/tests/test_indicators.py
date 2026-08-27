import pytest
import pytest_asyncio

# Use pytest-asyncio to handle async tests
from conftest import requires_redis
from httpx import AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@requires_redis
async def test_indicators_posture_endpoint(client):
    """Test indicators/ta endpoint, verifying calculations and scoring engine output."""
    # Query Apple technical analysis
    resp = await client.get("/api/v1/indicators/ta?symbol=AAPL")
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "AAPL"
    assert "close" in data
    assert "score" in data
    assert "rating" in data
    assert "summary" in data

    # Assert score is bounded correctly
    assert -100 <= data["score"] <= 100
    assert data["rating"] in ["BUY", "HOLD", "SELL"]

    # Verify signals components
    signals = data["signals"]
    assert "rsi" in signals
    assert "macd" in signals
    assert "trends" in signals
    assert "bollinger" in signals
    assert "volume" in signals

    # Check details of a single signal
    rsi_sig = signals["rsi"]
    assert "score" in rsi_sig
    assert "signal" in rsi_sig

    # Verify pivot point details are populated
    pivots = data["pivots"]
    assert pivots is not None
    assert "pivot" in pivots
    assert "r1" in pivots
    assert "s1" in pivots
    assert "r2" in pivots
    assert "s2" in pivots
