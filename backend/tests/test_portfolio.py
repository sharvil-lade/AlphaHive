import pytest

pytestmark = pytest.mark.asyncio


async def test_portfolio_lifecycle_endpoints(client):
    """Full CRUD lifecycle for holdings plus the summary calculations.

    Identity comes from the session cookie the client is issued on its first request,
    so no session id is passed anywhere.
    """
    # 1. Get or create the default portfolio for this session
    get_resp = await client.get("/api/v1/portfolios")
    assert get_resp.status_code == 200
    portfolio = get_resp.json()
    assert portfolio["name"] == "My AI Portfolio"
    assert portfolio["holdings"] == []

    # 2. Add a holding
    add_resp = await client.post(
        "/api/v1/portfolios/holdings",
        json={"symbol": "AAPL", "shares": 10.0, "average_buy_price": 150.00},
    )
    assert add_resp.status_code == 201
    holding = add_resp.json()
    assert holding["symbol"] == "AAPL"
    assert holding["shares"] == 10.0

    # 3. Adding the same symbol merges into a weighted average cost
    add_again = await client.post(
        "/api/v1/portfolios/holdings",
        json={"symbol": "AAPL", "shares": 10.0, "average_buy_price": 170.00},
    )
    assert add_again.status_code == 201
    merged = add_again.json()
    assert merged["shares"] == 20.0
    assert merged["average_buy_price"] == 160.00  # (10*150 + 10*170) / 20

    # 4. Add a second holding
    tsla = await client.post(
        "/api/v1/portfolios/holdings",
        json={"symbol": "TSLA", "shares": 5.0, "average_buy_price": 180.00},
    )
    assert tsla.status_code == 201
    tsla_id = tsla.json()["id"]

    # 5. Summary metrics
    summary_resp = await client.get("/api/v1/portfolios/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert len(summary["holdings"]) == 2
    assert summary["total_cost"] == (20.0 * 160.00) + (5.0 * 180.00)
    assert summary["total_value"] > 0
    for key in (
        "gain_loss",
        "gain_loss_percentage",
        "weighted_beta",
        "weighted_volatility",
        "sector_weights",
    ):
        assert key in summary

    # 6. Edit a holding
    edit_resp = await client.put(
        f"/api/v1/portfolios/holdings/{tsla_id}",
        json={"shares": 10.0, "average_buy_price": 175.00},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["shares"] == 10.0
    assert edit_resp.json()["average_buy_price"] == 175.00

    # 7. Delete it
    assert (await client.delete(f"/api/v1/portfolios/holdings/{tsla_id}")).status_code == 204

    # 8. Confirm the summary reflects the deletion
    after = (await client.get("/api/v1/portfolios/summary")).json()
    assert len(after["holdings"]) == 1
    assert after["holdings"][0]["symbol"] == "AAPL"
