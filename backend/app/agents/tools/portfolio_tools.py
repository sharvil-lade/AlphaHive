"""Portfolio tool — lets an agent read the user's own holdings.

This is what makes the assistant portfolio-aware: the master/supervisor can pull
the user's live holdings and reason about a question *in the context of what they
actually own* ("given my portfolio, should I add more Reliance?").

The tool opens its own short-lived DB session (agents run outside the request's
FastAPI dependency scope), so it is safe to call from inside the agent loop.
"""

import json

from langchain_core.tools import tool

from app.db.session import AsyncSessionLocal
from app.services.portfolio_service import portfolio_service


@tool
async def get_user_portfolio(session_id: str) -> str:
    """Get the current user's stock portfolio: holdings, value, cost, and gain/loss.

    Use this to ground advice in what the user actually owns — their positions,
    each position's current value and gain/loss, sector weights, and portfolio-level
    beta/volatility. `session_id` is the user's session identifier (provided in the
    system context). Returns JSON, or a note if the portfolio is empty.
    """
    async with AsyncSessionLocal() as db:
        summary = await portfolio_service.get_portfolio_summary(db, session_id)

    holdings = summary.get("holdings", [])
    if not holdings:
        return "The user's portfolio is empty — they have not added any holdings yet."

    return json.dumps(
        {
            "total_value": round(summary.get("total_value", 0.0), 2),
            "total_cost": round(summary.get("total_cost", 0.0), 2),
            "gain_loss": round(summary.get("gain_loss", 0.0), 2),
            "gain_loss_percentage": round(summary.get("gain_loss_percentage", 0.0), 2),
            "weighted_beta": round(summary.get("weighted_beta", 0.0), 3),
            "sector_weights": {
                k: round(v, 1) for k, v in (summary.get("sector_weights") or {}).items()
            },
            "holdings": [
                {
                    "symbol": h["symbol"],
                    "shares": h["shares"],
                    "average_buy_price": round(h["average_buy_price"], 2),
                    "current_price": round(h["current_price"], 2),
                    "value": round(h["total_value"], 2),
                    "gain_loss_pct": round(h["gain_loss_percentage"], 2),
                    "sector": h.get("sector"),
                }
                for h in holdings
            ],
        }
    )
