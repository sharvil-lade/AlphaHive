from typing import Dict, Any
from app.agents.state import AgentState
from app.services.stock_service import stock_service
from app.agents.utils import log_agent_activity, emit_chat_event
from app.agents.verdict import get_agent_verdict

async def research_node(state: AgentState) -> Dict[str, Any]:
    """Research node gathering fundamental metrics and quote profiles, then forming
    an independent fundamentals-analyst verdict on them (see agents/verdict.py)."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    message_id = state.get("message_id")

    start_log = await log_agent_activity(
        run_id,
        "research",
        f"Initializing fundamental research for ticker: {ticker}"
    )
    if message_id:
        await emit_chat_event(message_id, {"type": "agent-status", "node": "fundamentals", "status": "running"})

    try:
        quote = await stock_service.fetch_quote(ticker) or {}
        profile = await stock_service.fetch_profile(ticker) or {}

        quotes_data = {
            "price": quote.get("price", 0.0),
            "change": quote.get("change", 0.0),
            "percent_change": quote.get("percent_change", 0.0),
            "high": quote.get("high", 0.0),
            "low": quote.get("low", 0.0),
            "open": quote.get("open", 0.0),
            "previous_close": quote.get("previous_close", 0.0),
            "name": profile.get("name", ticker),
            "sector": profile.get("sector", "Unknown"),
            "industry": profile.get("industry", "Unknown"),
            "market_cap": profile.get("market_cap", 0.0)
        }

        verdict = await get_agent_verdict(
            role="a fundamentals analyst",
            data_summary=(
                f"Company: {quotes_data['name']} ({ticker}), sector {quotes_data['sector']}/"
                f"{quotes_data['industry']}. Price {quotes_data['price']} ({quotes_data['percent_change']:.2f}% "
                f"today), market cap {quotes_data['market_cap']}."
            ),
            rating_options='"BULLISH" | "NEUTRAL" | "BEARISH"',
            session_id=state.get("session_id"),
        )
        quotes_data["agent_verdict"] = verdict

        success_log = await log_agent_activity(
            run_id,
            "research",
            f"Successfully gathered fundamental data for {ticker}. Name: {quotes_data['name']}, "
            f"Price: ${quotes_data['price']}. Fundamentals agent verdict: {verdict['rating']} "
            f"({verdict['confidence']}%)."
        )
        if message_id:
            await emit_chat_event(message_id, {"type": "agent-status", "node": "fundamentals", "status": "completed"})

        return {
            "quotes": quotes_data,
            "logs": [start_log, success_log]
        }
    except Exception as e:
        error_log = await log_agent_activity(
            run_id,
            "research",
            f"Error during fundamental research: {e}"
        )
        if message_id:
            await emit_chat_event(message_id, {"type": "agent-status", "node": "fundamentals", "status": "failed"})
        return {
            "logs": [start_log, error_log]
        }
