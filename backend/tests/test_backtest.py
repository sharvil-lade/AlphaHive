import pytest
import pytest_asyncio
from httpx import AsyncClient

from backend.app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_backtest_rsi_strategy(client):
    """Test running backtest simulation with RSI strategy."""
    resp = await client.post(
        "/api/v1/backtest",
        json={
            "symbol": "AAPL",
            "strategy": "rsi",
            "initial_capital": 10000.0,
            "range_str": "1y"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["strategy"] == "rsi"
    assert data["initial_capital"] == 10000.0
    assert "total_return" in data
    assert "benchmark_return" in data
    assert "sharpe_ratio" in data
    assert "max_drawdown" in data
    assert "win_rate" in data
    assert "total_trades" in data
    assert len(data["equity_curve"]) > 10
    assert "portfolio_value" in data["equity_curve"][0]
    assert "benchmark_value" in data["equity_curve"][0]
    assert isinstance(data["trades"], list)


async def test_backtest_ema_crossover_strategy(client):
    """Test running backtest simulation with EMA Crossover strategy."""
    resp = await client.post(
        "/api/v1/backtest",
        json={
            "symbol": "MSFT",
            "strategy": "ema_crossover",
            "initial_capital": 5000.0,
            "range_str": "6mo"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "MSFT"
    assert data["strategy"] == "ema_crossover"
    assert data["initial_capital"] == 5000.0
    assert "total_return" in data
    assert "sharpe_ratio" in data
    assert len(data["equity_curve"]) > 10
    assert isinstance(data["trades"], list)
