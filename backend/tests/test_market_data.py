import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.models import Stock, StockPrice

# Use pytest-asyncio to handle async tests
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_check(client):
    """Test deep integration health check endpoint."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "connected" in data["postgres"]
    assert "connected" in data["redis"]
    assert "connected" in data["qdrant"]


async def test_stock_quote_endpoints(client):
    """Test real-time quote retrieval (Finnhub & yfinance fallback)."""
    # Query Apple
    resp = await client.get("/api/v1/stocks/quote?symbol=AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert "price" in data
    assert "change" in data
    assert "percent_change" in data
    assert "source" in data


async def test_company_profile_endpoints(client):
    """Test company profile fetching and PostgreSQL upsert."""
    resp = await client.get("/api/v1/stocks/profile?symbol=AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["name"] != ""
    assert "sector" in data
    assert "industry" in data

    # Wait for FastAPI to release database connection back to pool
    import asyncio
    await asyncio.sleep(0.2)

    # Verify record was upserted in PostgreSQL database
    from backend.app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Stock).where(Stock.symbol == "AAPL"))
        stock_record = res.scalar_one_or_none()
        assert stock_record is not None
        assert stock_record.symbol == "AAPL"
        assert stock_record.name != ""


async def test_historical_ohlcv_endpoints(client):
    """Test historical daily chart loading and PostgreSQL upserting."""
    resp = await client.get("/api/v1/stocks/history?symbol=MSFT&range_str=1mo")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    first_bar = data[0]
    assert "open" in first_bar
    assert "high" in first_bar
    assert "low" in first_bar
    assert "close" in first_bar
    assert "volume" in first_bar
    assert "date" in first_bar

    # Wait for FastAPI to release database connection back to pool
    import asyncio
    await asyncio.sleep(0.2)

    # Verify records were written into stock_prices table
    from backend.app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(StockPrice).where(StockPrice.symbol == "MSFT"))
        prices = res.scalars().all()
        assert len(prices) > 0
        assert prices[0].symbol == "MSFT"
