from fastapi import APIRouter, Query

from app.schemas.schemas import SentimentResponse
from app.services.sentiment_service import sentiment_service

router = APIRouter()


@router.get("/summary", response_model=SentimentResponse)
async def get_sentiment_summary(
    symbol: str = Query(..., description="Stock Ticker Symbol"),
    session_id: str | None = Query(None, description="Client Session ID"),
):
    """Get consolidated news and social sentiment analysis for a stock ticker symbol.

    Runs public Reddit scraping, aggregates news feeds, and parses sentiment using OpenAI or a lexical local analyzer.
    """
    sentiment = await sentiment_service.analyze_sentiment(symbol, session_id)
    return sentiment
