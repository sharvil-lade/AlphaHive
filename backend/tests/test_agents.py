import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import UUID

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_agent_run_execution_pipeline(client):
    """Test POST /agents/run to trigger workflow, and poll details until completed."""
    # 1. Trigger agent run
    resp = await client.post("/api/v1/agents/run?symbol=NVDA&session_id=test_integration_session")
    assert resp.status_code == 201
    run_data = resp.json()
    
    assert run_data["session_id"] == "test_integration_session"
    assert run_data["ticker"] == "NVDA"
    assert "id" in run_data
    assert run_data["status"] == "running"
    
    run_id = run_data["id"]
    
    # 2. Poll the detail endpoint until completed (timeout in 15 seconds)
    completed = False
    details = {}
    
    for _ in range(30):
        detail_resp = await client.get(f"/api/v1/agents/run/{run_id}")
        assert detail_resp.status_code == 200
        details = detail_resp.json()
        
        if details["status"] in ["completed", "failed"]:
            completed = True
            break
        await asyncio.sleep(0.5)
        
    assert completed, f"Agent execution timed out or failed to complete. Final status: {details.get('status')}"
    assert details["status"] == "completed"
    assert details["ticker"] == "NVDA"
    
    # 3. Check that parallel logs were merged and persisted
    logs = details["logs"]
    assert len(logs) > 0
    # Verify we got logs from multiple parallel workers
    nodes_logged = {l["node"] for l in logs}
    assert "orchestrator" in nodes_logged
    assert "research" in nodes_logged
    assert "technical" in nodes_logged
    assert "news" in nodes_logged
    assert "risk" in nodes_logged
    assert "decision" in nodes_logged
    
    # 4. Check report data
    report = details["report"]
    assert report is not None
    assert report["ticker"] == "NVDA"
    assert report["recommendation"] in ["buy", "hold", "sell"]
    assert 0 <= report["confidence_score"] <= 100
    assert len(report["content_markdown"]) > 0
