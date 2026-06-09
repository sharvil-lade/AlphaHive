from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.schemas import TechnicalPostureResponse
from backend.app.services.indicators_service import indicators_service
from backend.app.services.stock_service import stock_service
from backend.app.services.ta_scoring import ta_scoring

router = APIRouter()


@router.get("/ta", response_model=TechnicalPostureResponse)
async def get_technical_posture(symbol: str = Query(..., description="Stock Ticker Symbol")):
    """Get full technical indicators posture evaluation and consolidated posture rating.

    Performs SMA, EMA, RSI, MACD, and Bollinger Bands calculation, feeds metrics to the quantitative
    scoring matrix, and returns the aggregated score, signals, and pivot levels.
    """
    symbol = symbol.upper()
    
    # 1. Fetch live quote metrics for volume/price change checks
    quote = await stock_service.fetch_quote(symbol)
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote details not found for symbol: {symbol}"
        )

    # 2. Calculate indicators from historical pricing arrays
    indicators = await indicators_service.calculate_indicators(symbol)
    if not indicators:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not calculate technical indicators for symbol: {symbol}"
        )

    # 3. Evaluate posture utilizing quantitative matrix scoring
    posture = ta_scoring.evaluate_posture(indicators, quote)
    
    return posture
