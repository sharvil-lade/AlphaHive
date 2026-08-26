from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.schemas import IndexResponse, QueryResponse
from app.services.sec_service import sec_service
from app.utils.text_chunker import text_chunker
from app.services.vector_store import vector_store

router = APIRouter()


@router.post("/index", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def index_sec_filing(
    symbol: str = Query(..., description="Stock Ticker Symbol"),
    form_type: str = Query("10-K", description="Filing Form Type: 10-K, 10-Q")
):
    """Triggers downloading, segmenting, chunking, and embedding indexing of the latest SEC filing."""
    symbol = symbol.upper()
    form_type = form_type.upper()

    # 1. Fetch Raw filing text
    filing_text = await sec_service.fetch_latest_filing(symbol, form_type)
    if not filing_text:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find or retrieve {form_type} filing for symbol: {symbol}"
        )

    # 2. Segment and Chunk
    chunks = text_chunker.segment_and_chunk(filing_text)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parsed filing text yielded 0 chunks for indexing."
        )

    # 3. Upsert into Qdrant Vector store
    try:
        await vector_store.upsert_document_chunks(symbol, chunks)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upsert chunks into Qdrant: {e}"
        )

    return {
        "symbol": symbol,
        "form_type": form_type,
        "status": "indexed",
        "chunks_indexed": len(chunks)
    }


@router.get("/query", response_model=QueryResponse)
async def query_sec_rag(
    symbol: str = Query(..., description="Stock Ticker Symbol"),
    query: str = Query(..., description="Natural language search query"),
    limit: int = Query(5, description="Maximum matches to return")
):
    """Retrieve cited footnotes or paragraph matches for a stock ticker symbol matching the search query."""
    symbol = symbol.upper()
    try:
        matches = await vector_store.search_chunks(symbol, query, limit)
        return {
            "symbol": symbol,
            "query": query,
            "matches": matches
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector similarity query failed: {e}"
        )
