import pytest

pytestmark = pytest.mark.asyncio


async def test_sec_indexing_endpoint(client):
    """POST /sec/index downloads, chunks and stores a filing in sec_chunks."""
    resp = await client.post("/api/v1/sec/index?symbol=AAPL&form_type=10-K")
    assert resp.status_code == 201, resp.json()
    data = resp.json()

    assert data["symbol"] == "AAPL"
    assert data["form_type"] == "10-K"
    assert data["status"] == "indexed"
    assert data["chunks_indexed"] > 0


async def test_sec_query_returns_ranked_matches(client):
    """GET /sec/query ranks the indexed chunks and returns cited excerpts.

    Phrased as a sentence on purpose: the keyword path ORs its terms, so a partial
    overlap still ranks. An AND-based tsquery would return nothing here.
    """
    index_resp = await client.post("/api/v1/sec/index?symbol=TSLA&form_type=10-K")
    assert index_resp.status_code == 201

    resp = await client.get("/api/v1/sec/query?symbol=TSLA&query=price cuts and profit margins&limit=3")
    assert resp.status_code == 200, resp.json()
    data = resp.json()

    assert data["symbol"] == "TSLA"
    assert data["query"]
    assert 0 < len(data["matches"]) <= 3

    first_match = data["matches"][0]
    assert first_match.keys() >= {"text", "section", "score", "chunk_id"}
    assert first_match["score"] > 0


async def test_sec_query_unknown_symbol_is_empty(client):
    """A ticker with nothing indexed returns no matches rather than an error."""
    resp = await client.get("/api/v1/sec/query?symbol=ZZZZ&query=liquidity risk")
    assert resp.status_code == 200
    assert resp.json()["matches"] == []


async def test_indexing_is_idempotent(client):
    """Re-indexing the same filing replaces its chunks instead of duplicating them."""
    first = await client.post("/api/v1/sec/index?symbol=MSFT&form_type=10-K")
    second = await client.post("/api/v1/sec/index?symbol=MSFT&form_type=10-K")
    assert first.status_code == second.status_code == 201
    assert first.json()["chunks_indexed"] == second.json()["chunks_indexed"]
