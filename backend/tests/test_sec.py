import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.main import app

# Use pytest-asyncio to handle async tests
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_sec_indexing_endpoint(client):
    """Test POST /sec/index endpoint, verifying file downloading, chunking, and Qdrant upserts."""
    # Index Apple 10-K (triggers download + mock fallbacks + Qdrant upload)
    resp = await client.post("/api/v1/sec/index?symbol=AAPL&form_type=10-K")
    assert resp.status_code == 201
    data = resp.json()

    assert data["symbol"] == "AAPL"
    assert data["form_type"] == "10-K"
    assert data["status"] == "indexed"
    assert data["chunks_indexed"] > 0


async def test_sec_query_rag_endpoint(client):
    """Test GET /sec/query endpoint, verifying semantic chunk matches and payload metadata."""
    # First, make sure TSLA is indexed
    index_resp = await client.post("/api/v1/sec/index?symbol=TSLA&form_type=10-K")
    assert index_resp.status_code == 201

    # Query Tesla price risks
    resp = await client.get("/api/v1/sec/query?symbol=TSLA&query=price cuts and profit margins&limit=3")
    assert resp.status_code == 200, resp.json()
    data = resp.json()

    assert data["symbol"] == "TSLA"
    assert "query" in data
    assert len(data["matches"]) > 0
    assert len(data["matches"]) <= 3

    # Check match structure
    first_match = data["matches"][0]
    assert "text" in first_match
    assert "section" in first_match
    assert "score" in first_match
    assert "chunk_id" in first_match
