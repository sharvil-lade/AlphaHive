"""Technical-analysis tool — indicators + a deterministic posture score."""

import json

from langchain_core.tools import tool

from app.services.indicators_service import indicators_service
from app.services.stock_service import stock_service
from app.services.ta_scoring import ta_scoring


@tool
async def get_technical_analysis(symbol: str) -> str:
    """Get technical indicators and a bullish/bearish posture for a stock ticker.

    Computes RSI, MACD, Bollinger Bands, moving averages and pivot levels, then a
    deterministic BUY/HOLD/SELL posture with a numeric score and per-signal
    breakdown. Use this to judge momentum and trend. `symbol` is the ticker.
    Returns JSON, or an error note if there is not enough price history.
    """
    indicators = await indicators_service.calculate_indicators(symbol)
    if not indicators:
        return f"Not enough price history to compute technical indicators for {symbol}."

    quote = await stock_service.fetch_quote(symbol) or {}
    posture = ta_scoring.evaluate_posture(indicators, quote)

    return json.dumps(
        {
            "symbol": symbol.upper(),
            "rating": posture.get("rating"),
            "score": posture.get("score"),
            "signals": posture.get("signals"),
            "rsi": indicators.get("rsi"),
            "macd": indicators.get("macd"),
            "macd_signal": indicators.get("macd_signal"),
            "sma_20": indicators.get("sma_20"),
            "sma_50": indicators.get("sma_50"),
            "close": indicators.get("close"),
        }
    )
