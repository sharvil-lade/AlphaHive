import asyncio
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


async def test_reports_history_and_download_endpoints(client):
    """Test report generation, history lookup, markdown download, and xhtml2pdf PDF rendering."""
    # 1. Trigger agent run for a unique session ID
    session_id = "test_reports_session_id_123"
    post_resp = await client.post(f"/api/v1/agents/run?symbol=AAPL&session_id={session_id}")
    assert post_resp.status_code == 201
    run_data = post_resp.json()
    run_id = run_data["id"]
    
    # 2. Wait for background task to write postgres rows
    completed = False
    for _ in range(30):
        detail_resp = await client.get(f"/api/v1/agents/run/{run_id}")
        assert detail_resp.status_code == 200
        details = detail_resp.json()
        if details["status"] in ["completed", "failed"]:
            completed = True
            break
        await asyncio.sleep(0.5)
        
    assert completed, "Agent execution timed out during report test."
    assert details["status"] == "completed"
    
    # 3. Test reports history lookup
    hist_resp = await client.get(f"/api/v1/reports/history?session_id={session_id}")
    assert hist_resp.status_code == 200
    history_items = hist_resp.json()
    
    assert len(history_items) > 0
    item = history_items[0]
    assert item["run_id"] == run_id
    assert item["ticker"] == "AAPL"
    assert item["status"] == "completed"
    assert "recommendation" in item
    assert "confidence_score" in item
    
    # 4. Test Markdown download endpoint
    md_resp = await client.get(f"/api/v1/reports/{run_id}/markdown")
    assert md_resp.status_code == 200
    assert md_resp.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "attachment" in md_resp.headers["content-disposition"]
    assert "Investment_Memo_AAPL" in md_resp.headers["content-disposition"]
    assert len(md_resp.content) > 0
    
    # 5. Test PDF download endpoint (verifies xhtml2pdf compile)
    pdf_resp = await client.get(f"/api/v1/reports/{run_id}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert "attachment" in pdf_resp.headers["content-disposition"]
    assert "Investment_Memo_AAPL" in pdf_resp.headers["content-disposition"]
    
    # Verify PDF magic bytes
    assert pdf_resp.content.startswith(b"%PDF-")
