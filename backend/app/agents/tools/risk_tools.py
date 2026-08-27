"""Risk tools — statistical risk metrics and SEC filing retrieval."""

import json

import numpy as np
from langchain_core.tools import tool

from app.services import sec_index
from app.services.stock_service import stock_service

# Beta benchmark: Nifty 50 for Indian tickers (URL-encoded "^NSEI"), S&P 500 (SPY)
# for everything else.
_INDIA_BENCHMARK_SYMBOL = "%5ENSEI"
_US_BENCHMARK_SYMBOL = "SPY"


@tool
async def get_risk_metrics(symbol: str) -> str:
    """Get statistical risk metrics for a stock: beta and annualised volatility.

    Beta is measured against Nifty 50 for Indian tickers and the S&P 500 otherwise.
    Volatility is annualised from ~1 year of daily returns. Use this to judge how
    risky/volatile a stock is versus the market. `symbol` is the ticker. Returns JSON.
    """
    benchmark = (
        _INDIA_BENCHMARK_SYMBOL if stock_service.resolve_market(symbol) == "IN" else _US_BENCHMARK_SYMBOL
    )
    beta = 1.0
    annualized_vol = 0.0
    history_days = 0

    try:
        stock_history = await stock_service.fetch_history(symbol, range_str="1y")
        benchmark_history = await stock_service.fetch_history(benchmark, range_str="1y")

        if len(stock_history) > 10:
            closes = [h["close"] for h in stock_history]
            returns = np.diff(closes) / np.array(closes[:-1])
            annualized_vol = float(np.std(returns) * np.sqrt(252))
            history_days = len(stock_history)

            stock_by_date = {h["date"]: h["close"] for h in stock_history}
            bench_by_date = {h["date"]: h["close"] for h in benchmark_history}
            common = sorted(set(stock_by_date) & set(bench_by_date))
            if len(common) > 10:
                s = np.array([stock_by_date[d] for d in common])
                b = np.array([bench_by_date[d] for d in common])
                s_ret = np.diff(s) / s[:-1]
                b_ret = np.diff(b) / b[:-1]
                cov = np.cov(s_ret, b_ret)[0][1]
                b_var = np.var(b_ret)
                beta = float(cov / b_var) if b_var > 0 else 1.0
    except Exception as e:  # noqa: BLE001 — tool must never raise into the agent loop
        return f"Could not compute risk metrics for {symbol}: {e}"

    if history_days == 0:
        return f"Not enough price history to compute risk metrics for {symbol}."

    return json.dumps(
        {
            "symbol": symbol.upper(),
            "beta": round(beta, 3),
            "annualized_volatility_pct": round(annualized_vol * 100, 2),
            "benchmark": "Nifty 50" if benchmark == _INDIA_BENCHMARK_SYMBOL else "S&P 500",
            "history_days": history_days,
        }
    )


@tool
async def search_sec_filings(symbol: str, query: str) -> str:
    """Search indexed SEC filings (10-K/10-Q) for a stock and return relevant excerpts.

    Use to pull management's own disclosed risk factors, competition, and liabilities.
    `symbol` is the ticker; `query` is what to look for (e.g. "regulatory risk,
    competition, litigation"). Returns the top matching excerpts, or a note if the
    ticker has no filings indexed (only a small ticker set is currently indexed).
    """
    try:
        results = await sec_index.search(symbol, query, limit=3)
    except Exception as e:  # noqa: BLE001
        return f"SEC filing search unavailable for {symbol}: {e}"

    if not results:
        return f"No SEC filing excerpts indexed for {symbol}."

    excerpts = [
        {
            "section": r.get("section", "Risk Factors"),
            "text": (r.get("text", "") or "")[:400],
        }
        for r in results
    ]
    return json.dumps({"symbol": symbol.upper(), "excerpts": excerpts})
