from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.schemas import QuoteResponse, NewsResponse, StockSchema, StockPriceSchema
from app.services.stock_service import stock_service
from app.services.news_service import news_service
from app.services.db_service import db_service

router = APIRouter()


@router.get("/quote", response_model=QuoteResponse)
async def get_stock_quote(symbol: str = Query(..., description="Stock Ticker Symbol")):
    """Get real-time quote metrics for a stock ticker symbol.

    Leverages Redis caching and falls back to public Yahoo Finance chart queries if rate-limited.
    """
    quote = await stock_service.fetch_quote(symbol)
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock quote details not found for symbol: {symbol}"
        )
    return quote


@router.get("/profile", response_model=StockSchema)
async def get_company_profile(
    symbol: str = Query(..., description="Stock Ticker Symbol"),
    db: AsyncSession = Depends(get_db)
):
    """Get company general profile information.

    Caches results in Redis and persists basic company metadata records in PostgreSQL.
    """
    profile = await stock_service.fetch_profile(symbol)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company profile details not found for symbol: {symbol}"
        )
    
    # Persist company metadata in PostgreSQL database asynchronously
    try:
        await db_service.upsert_stock(
            db=db,
            symbol=profile["symbol"],
            name=profile["name"],
            sector=profile["sector"],
            industry=profile["industry"]
        )
    except Exception as e:
        # Log error but do not fail the request
        import logging
        logging.getLogger("stocks-api").error(f"Failed to upsert stock metadata for {symbol}: {e}")

    return {
        "symbol": profile["symbol"],
        "name": profile["name"],
        "sector": profile["sector"],
        "industry": profile["industry"]
    }


@router.get("/news", response_model=List[NewsResponse])
async def get_stock_news(symbol: str = Query(..., description="Stock Ticker Symbol")):
    """Get top company news articles from Finnhub company-news or public Yahoo Finance search API."""
    news = await news_service.fetch_news(symbol)
    return news


@router.get("/history", response_model=List[StockPriceSchema])
async def get_stock_history(
    symbol: str = Query(..., description="Stock Ticker Symbol"),
    interval: str = Query("1d", description="Time interval: 1d, 1wk"),
    range_str: str = Query("1mo", description="Historical range: 1mo, 3mo, 6mo, 1y"),
    db: AsyncSession = Depends(get_db)
):
    """Get historical daily price quotes (OHLCV).

    Saves/updates daily stock prices in PostgreSQL and caches response payloads in Redis.
    """
    # 1. Fetch normalized chart history from external providers/fallbacks
    history = await stock_service.fetch_history(symbol, interval, range_str)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historical price quotes not found for symbol: {symbol}"
        )

    # 2. Persist daily OHLCV quotes in PostgreSQL asynchronously
    try:
        # Assure stock metadata is upserted first to resolve foreign key constraints
        profile = await stock_service.fetch_profile(symbol)
        await db_service.upsert_stock(
            db=db,
            symbol=symbol,
            name=profile.get("name", symbol),
            sector=profile.get("sector"),
            industry=profile.get("industry")
        )
        
        # Bulk upsert the historical prices
        await db_service.save_historical_prices(db=db, symbol=symbol, prices_list=history)
    except Exception as e:
        import logging
        logging.getLogger("stocks-api").error(f"Failed to persist historical price series for {symbol}: {e}")

    # 3. Retrieve stored prices to guarantee consistency with SQLAlchemy models schema mapping
    stored_prices = await db_service.get_stored_prices(db=db, symbol=symbol, limit=len(history))
    
    # Fallback to direct mapping if DB fetch yielded less rows than expected
    if len(stored_prices) < len(history):
        # Return converted objects manually to satisfy schema constraints
        import uuid
        return [
            {
                "id": uuid.uuid4(),
                "symbol": item["symbol"],
                "date": item["date"],
                "open": item["open"],
                "high": item["high"],
                "low": item["low"],
                "close": item["close"],
                "volume": item["volume"]
            }
            for item in history
        ]

    return stored_prices
