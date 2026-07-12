import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


import uuid

async def test_watchlist_and_alerts_lifecycle(client):
    """Test watchlist tracking and alerts rule criteria evaluation engine."""
    session_id = f"test_automation_session_{uuid.uuid4().hex}"
    
    # 1. Watchlist GET is initially empty
    get_wl_resp = await client.get(f"/api/v1/watchlist?session_id={session_id}")
    assert get_wl_resp.status_code == 200
    assert len(get_wl_resp.json()) == 0
    
    # 2. Add TSLA to watchlist
    add_wl_resp = await client.post(
        f"/api/v1/watchlist?session_id={session_id}",
        json={"symbol": "TSLA"}
    )
    assert add_wl_resp.status_code == 201
    wl_item = add_wl_resp.json()
    assert wl_item["symbol"] == "TSLA"
    assert wl_item["session_id"] == session_id
    
    # 3. Create price alert for TSLA above $100
    alert1_resp = await client.post(
        f"/api/v1/alerts?session_id={session_id}",
        json={
            "symbol": "TSLA",
            "trigger_type": "price_above",
            "trigger_value": 100.00
        }
    )
    assert alert1_resp.status_code == 201
    alert1 = alert1_resp.json()
    assert alert1["symbol"] == "TSLA"
    assert alert1["trigger_type"] == "price_above"
    assert alert1["trigger_value"] == 100.00
    assert alert1["is_active"] is True
    
    # 4. Create rsi alert for TSLA below 20
    alert2_resp = await client.post(
        f"/api/v1/alerts?session_id={session_id}",
        json={
            "symbol": "TSLA",
            "trigger_type": "rsi_below",
            "trigger_value": 20.0
        }
    )
    assert alert2_resp.status_code == 201
    alert2 = alert2_resp.json()
    assert alert2["is_active"] is True
    alert2_id = alert2["id"]
    
    # 5. List active alerts
    list_active = await client.get(f"/api/v1/alerts?session_id={session_id}&active_only=true")
    assert list_active.status_code == 200
    assert len(list_active.json()) == 2
    
    # 6. Execute checker scan
    # For TSLA, price is around 168.40 (mock), so price_above 100.00 will trigger!
    # RSI is 35 (mock), so rsi_below 20.0 will NOT trigger!
    check_resp = await client.post("/api/v1/alerts/check")
    assert check_resp.status_code == 200
    triggered = check_resp.json()
    
    # Check that TSLA price_above alert triggered
    assert len(triggered) >= 1
    triggered_ids = [t["alert_id"] for t in triggered]
    assert alert1["id"] in triggered_ids
    
    # 7. List active alerts after scan (should show 1 active, 1 triggered/inactive)
    list_active_after = await client.get(f"/api/v1/alerts?session_id={session_id}&active_only=true")
    assert list_active_after.status_code == 200
    assert len(list_active_after.json()) == 1
    assert list_active_after.json()[0]["id"] == alert2_id
    
    # List all alerts (should show 2)
    list_all = await client.get(f"/api/v1/alerts?session_id={session_id}&active_only=false")
    assert list_all.status_code == 200
    assert len(list_all.json()) == 2
    
    # 8. Cancel active alert
    del_alert_resp = await client.delete(f"/api/v1/alerts/{alert2_id}?session_id={session_id}")
    assert del_alert_resp.status_code == 204
    
    # 9. Delete symbol from watchlist
    del_wl_resp = await client.delete(f"/api/v1/watchlist/TSLA?session_id={session_id}")
    assert del_wl_resp.status_code == 204
    
    # 10. Verify watchlist is empty
    get_wl_final = await client.get(f"/api/v1/watchlist?session_id={session_id}")
    assert len(get_wl_final.json()) == 0
