import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.schemas import IndexResponse, QueryResponse
from app.services import sec_index
from app.services.sec_service import sec_service
from app.utils.text_chunker import text_chunker

router = APIRouter()
logger = logging.getLogger("sec-api")


@router.post("/index", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def index_sec_filing(
    symbol: str = Query(..., description="Stock Ticker Symbol"),
    form_type: str = Query("10-K", description="Filing Form Type: 10-K, 10-Q"),
):
    """Download the latest filing, chunk it, and index the chunks for search."""
    symbol = symbol.upper()
    form_type = form_type.upper()

    filing_text = await sec_service.fetch_latest_filing(symbol, form_type)
    if not filing_text:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find or retrieve {form_type} filing for symbol: {symbol}",
        )

    chunks = text_chunker.segment_and_chunk(filing_text)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parsed filing text yielded 0 chunks for indexing.",
        )

    try:
        indexed = await sec_index.index_chunks(symbol, chunks)
    except Exception as e:
        logger.exception(f"Failed to index {form_type} chunks for {symbol}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not index this filing. Please try again.",
        ) from e

    return {"symbol": symbol, "form_type": form_type, "status": "indexed", "chunks_indexed": indexed}


@router.get("/query", response_model=QueryResponse)
async def query_sec_rag(
    symbol: str = Query(..., description="Stock Ticker Symbol"),
    query: str = Query(..., description="Natural language search query"),
    limit: int = Query(5, description="Maximum matches to return"),
):
    """Return the filing excerpts that best match the query, with their section."""
    symbol = symbol.upper()
    try:
        matches = await sec_index.search(symbol, query, limit)
    except Exception as e:
        logger.exception(f"SEC search failed for {symbol}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Filing search is temporarily unavailable.",
        ) from e

    return {"symbol": symbol, "query": query, "matches": matches}
