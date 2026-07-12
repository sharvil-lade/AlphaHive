import json
import logging
import re
from typing import Any, Dict, List

from app.agents.state import AgentState
from app.agents.utils import log_agent_activity, emit_chat_event
from app.services.llm_client import llm_client
from app.services.stock_service import INDIAN_TICKER_HINTS

logger = logging.getLogger("router-node")

# Small fallback whitelist for the no-LLM-configured degraded path only — the LLM
# path above handles the general case (company names, any ticker, typos, etc.).
_US_TICKER_HINTS = {"AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "GOOG", "META"}

ROUTER_SYSTEM_PROMPT = (
    "You are a query router for a stock market research assistant. Given a user's "
    "free-form message, extract structured routing information. Respond with JSON only."
)


def _build_router_prompt(query: str) -> str:
    return (
        f'User message: "{query}"\n\n'
        "Determine:\n"
        "1. tickers: a list of stock ticker symbols mentioned or clearly implied (company names -> "
        'their ticker, e.g. "Reliance" -> "RELIANCE", "Apple" -> "AAPL", "TCS" -> "TCS"). '
        "Empty list if no specific company/stock is being asked about.\n"
        '2. market: "IN" if the tickers/companies are Indian (NSE/BSE listed), "US" if US-listed, '
        '"IN" as the default if ambiguous (Indian markets are this app\'s primary focus).\n'
        '3. intent: "analysis" (wants a recommendation/analysis on one stock), "comparison" '
        '(comparing multiple stocks), or "general_question" (broader market question, definition, '
        "or anything not about a single specific stock's buy/sell case).\n"
        "4. needs_agents: true if answering well requires running fundamental/technical/sentiment/risk "
        "analysis on a specific ticker; false for general questions, definitions, or casual chat that "
        "a direct answer can handle.\n\n"
        "Respond with JSON only:\n"
        "{\n"
        '  "tickers": ["..."],\n'
        '  "market": "IN" | "US",\n'
        '  "intent": "analysis" | "comparison" | "general_question",\n'
        '  "needs_agents": true | false\n'
        "}"
    )


def _fallback_extract_tickers(query: str) -> List[str]:
    """Degraded-mode ticker extraction (no LLM configured) — checks uppercase-ish
    tokens in the query against the known ticker hint sets."""
    candidates = re.findall(r"[A-Za-z]{2,10}", query)
    found = []
    for word in candidates:
        upper = word.upper()
        if upper in INDIAN_TICKER_HINTS or upper in _US_TICKER_HINTS:
            found.append(upper)
    return found


async def router_node(state: AgentState) -> Dict[str, Any]:
    """Entry point for the chat graph: classifies a free-form query into
    tickers/market/intent, deciding whether to fan out to the specialist agents
    or short-circuit straight to synthesis for general/non-ticker questions."""
    query = state["query"]
    message_id = state["message_id"]

    start_log = await log_agent_activity(message_id, "router", f"Understanding query: {query[:120]}")
    await emit_chat_event(message_id, {"type": "agent-status", "node": "router", "status": "running"})

    tickers: List[str] = []
    market = "IN"
    intent = "general_question"
    needs_agents = False

    if llm_client.is_configured:
        result = await llm_client.complete(
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": _build_router_prompt(query)},
            ],
            json_mode=True,
            session_id=state.get("session_id"),
        )
        if result:
            try:
                parsed = json.loads(result.content)
                tickers = [str(t).upper() for t in parsed.get("tickers", []) if t]
                market = str(parsed.get("market", "IN")).upper()
                intent = str(parsed.get("intent", "general_question"))
                needs_agents = bool(parsed.get("needs_agents", False)) and bool(tickers)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.error(f"Failed to parse router response: {e}")
    else:
        tickers = _fallback_extract_tickers(query)
        if tickers:
            intent = "analysis"
            needs_agents = True

    # v1 only guarantees correctness for a single primary ticker — the state/graph
    # is structurally ready for multi-ticker comparisons later.
    primary_ticker = tickers[0] if tickers else ""

    success_log = await log_agent_activity(
        message_id,
        "router",
        f"Identified tickers={tickers or 'none'}, market={market}, intent={intent}, needs_agents={needs_agents}",
    )
    await emit_chat_event(message_id, {"type": "agent-status", "node": "router", "status": "completed"})

    return {
        "ticker": primary_ticker,
        "market": market,
        "intent": intent,
        "needs_agents": needs_agents,
        "logs": [start_log, success_log],
    }
