"""Fundamentals tools — live price quote and company profile."""

import json

from langchain_core.tools import tool

from app.services.stock_service import stock_service


@tool
async def get_stock_quote(symbol: str) -> str:
    """Get the latest real-time price quote for a stock ticker.

    Use for the current price, day change, day high/low, open, and previous close.
    `symbol` is the ticker (e.g. "RELIANCE", "TCS", "AAPL"); Indian tickers do not
    need a .NS/.BO suffix. Returns JSON, or an error note if no data source has it.
    """
    quote = await stock_service.fetch_quote(symbol)
    if not quote:
        return f"No live quote available for {symbol} from any data source."
    return json.dumps(
        {
            "symbol": symbol.upper(),
            "price": quote.get("price"),
            "change": quote.get("change"),
            "percent_change": quote.get("percent_change"),
            "day_high": quote.get("high"),
            "day_low": quote.get("low"),
            "open": quote.get("open"),
            "previous_close": quote.get("previous_close"),
            "source": quote.get("source"),
        }
    )


@tool
async def get_company_profile(symbol: str) -> str:
    """Get company fundamentals: name, sector, industry, and market capitalisation.

    Use to understand what the company does and how large it is. `symbol` is the
    ticker (e.g. "INFY", "MSFT"). Returns JSON, or an error note if unavailable.
    """
    profile = await stock_service.fetch_profile(symbol)
    if not profile:
        return f"No company profile available for {symbol}."
    return json.dumps(
        {
            "symbol": symbol.upper(),
            "name": profile.get("name"),
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "market_cap": profile.get("market_cap"),
            "website": profile.get("website"),
            "source": profile.get("source"),
        }
    )
