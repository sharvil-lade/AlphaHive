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


async def test_portfolio_lifecycle_endpoints(client):
    """Test entire CRUD lifecycle for portfolio holdings and summary calculations."""
    session_id = "test_portfolio_session_999"
    
    # 1. Get or create default portfolio
    get_resp = await client.get(f"/api/v1/portfolios?session_id={session_id}")
    assert get_resp.status_code == 200
    portfolio = get_resp.json()
    assert portfolio["session_id"] == session_id
    assert portfolio["name"] == "My AI Portfolio"
    assert len(portfolio["holdings"]) == 0
    
    # 2. Add holding (AAPL, 10 shares @ $150.00)
    add_payload = {
        "symbol": "AAPL",
        "shares": 10.0,
        "average_buy_price": 150.00
    }
    add_resp = await client.post(
        f"/api/v1/portfolios/holdings?session_id={session_id}",
        json=add_payload
    )
    assert add_resp.status_code == 201
    holding = add_resp.json()
    assert holding["symbol"] == "AAPL"
    assert holding["shares"] == 10.0
    assert holding["average_buy_price"] == 150.00
    holding_id = holding["id"]
    
    # 3. Add same holding (updates average price and shares)
    add_again_payload = {
        "symbol": "AAPL",
        "shares": 10.0,
        "average_buy_price": 170.00
    }
    add_again_resp = await client.post(
        f"/api/v1/portfolios/holdings?session_id={session_id}",
        json=add_again_payload
    )
    assert add_again_resp.status_code == 201
    updated_holding = add_again_resp.json()
    assert updated_holding["symbol"] == "AAPL"
    assert updated_holding["shares"] == 20.0
    assert updated_holding["average_buy_price"] == 160.00 # (10*150 + 10*170)/20 = 160.00
    
    # 4. Add a second holding (TSLA, 5 shares @ $180.00)
    add_tsla_payload = {
        "symbol": "TSLA",
        "shares": 5.0,
        "average_buy_price": 180.00
    }
    add_tsla_resp = await client.post(
        f"/api/v1/portfolios/holdings?session_id={session_id}",
        json=add_tsla_payload
    )
    assert add_tsla_resp.status_code == 201
    tsla_holding = add_tsla_resp.json()
    tsla_holding_id = tsla_holding["id"]
    
    # 5. Fetch Summary and assert metrics calculations
    summary_resp = await client.get(f"/api/v1/portfolios/summary?session_id={session_id}")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["name"] == "My AI Portfolio"
    assert len(summary["holdings"]) == 2
    assert summary["total_cost"] == (20.0 * 160.00) + (5.0 * 180.00) # 3200 + 900 = 4100.00
    assert summary["total_value"] > 0
    assert "gain_loss" in summary
    assert "gain_loss_percentage" in summary
    assert "weighted_beta" in summary
    assert "weighted_volatility" in summary
    assert "sector_weights" in summary
    
    # 6. Put/Edit holding (TSLA, change to 10 shares @ $175.00)
    edit_payload = {
        "shares": 10.0,
        "average_buy_price": 175.00
    }
    edit_resp = await client.put(
        f"/api/v1/portfolios/holdings/{tsla_holding_id}",
        json=edit_payload
    )
    assert edit_resp.status_code == 200
    edited_holding = edit_resp.json()
    assert edited_holding["shares"] == 10.0
    assert edited_holding["average_buy_price"] == 175.00
    
    # 7. Delete TSLA holding
    del_resp = await client.delete(f"/api/v1/portfolios/holdings/{tsla_holding_id}")
    assert del_resp.status_code == 204
    
    # 8. Verify deletion in summary
    summary_after_del_resp = await client.get(f"/api/v1/portfolios/summary?session_id={session_id}")
    assert summary_after_del_resp.status_code == 200
    summary_after_del = summary_after_del_resp.json()
    assert len(summary_after_del["holdings"]) == 1
    assert summary_after_del["holdings"][0]["symbol"] == "AAPL"
