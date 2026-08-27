import pytest
from conftest import requires_redis
from sqlalchemy.future import select

from app.models.models import Stock, StockPrice

pytestmark = pytest.mark.asyncio


@requires_redis
async def test_health_check(client):
    """The deep readiness probe reports every backing service it depends on."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "connected" in data["postgres"]
    assert "connected" in data["redis"]


@requires_redis
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


@requires_redis
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
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Stock).where(Stock.symbol == "AAPL"))
        stock_record = res.scalar_one_or_none()
        assert stock_record is not None
        assert stock_record.symbol == "AAPL"
        assert stock_record.name != ""


@requires_redis
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
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(StockPrice).where(StockPrice.symbol == "MSFT"))
        prices = res.scalars().all()
        assert len(prices) > 0
        assert prices[0].symbol == "MSFT"
