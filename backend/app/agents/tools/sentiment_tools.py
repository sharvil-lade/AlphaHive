"""News & social sentiment tool."""

import json

from langchain_core.tools import tool

from app.services.sentiment_service import sentiment_service


@tool
async def get_news_sentiment(symbol: str) -> str:
    """Get aggregated news + social-media sentiment for a stock ticker.

    Pulls recent financial headlines and social posts and returns a sentiment
    score (-100 bearish .. +100 bullish), a BUY/HOLD/SELL rating, a short summary,
    and lists of opportunities and threats. Use this to gauge the current narrative
    around a stock. `symbol` is the ticker. Returns JSON.
    """
    sentiment = await sentiment_service.analyze_sentiment(symbol)
    return json.dumps(
        {
            "symbol": symbol.upper(),
            "score": sentiment.get("score"),
            "rating": sentiment.get("rating"),
            "summary": sentiment.get("summary"),
            "opportunities": sentiment.get("opportunities", []),
            "threats": sentiment.get("threats", []),
            "source": sentiment.get("source"),
        }
    )
