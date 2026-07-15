"""Chat-graph nodes for the master–slave agentic architecture.

Each node here wraps a real agent (see `app/agents/specialists.py`) and emits the
SSE `agent-status` events the frontend trace panel listens for. The graph wiring
lives in `app/agents/graph.py:create_chat_graph`.

Flow:
    supervisor (master)  -> plans tickers + which specialists to dispatch
      -> fundamentals / technical / news_sentiment / risk  (slaves, run in parallel)
        -> synthesis (master)  -> streams the final portfolio-aware decision
"""

import asyncio
import logging
from typing import Any, Dict

from app.agents.specialists import (
    SPECIALIST_AGENTS,
    SPECIALIST_KEYS,
    master_supervisor,
)
from app.agents.llm import is_agent_llm_configured
from app.agents.state import AgentState
from app.agents.utils import emit_chat_event, log_agent_activity

logger = logging.getLogger("chat-nodes")

# Wall-clock guard so one hung agent can't stall the whole turn.
_AGENT_TIMEOUT = 75.0

# Human-readable labels used in logs / SSE.
_LABELS = {
    "fundamentals": "Fundamentals",
    "technical": "Technical",
    "news_sentiment": "News & Sentiment",
    "risk": "Risk",
}


def _last_message_text(result: Dict[str, Any]) -> str:
    """Pull the final assistant text out of a react-agent result."""
    messages = result.get("messages") or []
    if not messages:
        return ""
    last = messages[-1]
    content = getattr(last, "content", last if isinstance(last, str) else "")
    if isinstance(content, list):  # some providers return content parts
        content = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )
    return str(content).strip()


async def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """Master agent: reads the query + portfolio context and plans the work."""
    message_id = state["message_id"]
    query = state["query"]
    portfolio_context = state.get("portfolio_context") or "The user's portfolio is empty."

    start_log = await log_agent_activity(message_id, "supervisor", f"Master planning for: {query[:120]}")
    await emit_chat_event(message_id, {"type": "agent-status", "node": "supervisor", "status": "running"})

    tickers: list[str] = []
    selected_agents: list[str] = []
    market = "IN"
    needs_agents = False

    if is_agent_llm_configured():
        try:
            prompt = (
                f"User question: \"{query}\"\n\n"
                f"User's portfolio summary:\n{portfolio_context}\n\n"
                f"The user's session_id is \"{state.get('session_id', '')}\" — pass it to the "
                "get_user_portfolio tool if you need live holdings.\n"
                "Now produce your plan."
            )
            result = await asyncio.wait_for(
                master_supervisor().ainvoke({"messages": [{"role": "user", "content": prompt}]}),
                timeout=_AGENT_TIMEOUT,
            )
            plan = result.get("structured_response")
            if plan is not None:
                needs_agents = bool(plan.needs_research)
                tickers = [t.upper().strip() for t in (plan.tickers or []) if t]
                market = plan.market or "IN"
                selected_agents = [a for a in (plan.selected_agents or []) if a in SPECIALIST_KEYS]
                # A genuine analysis with no explicit agent list -> run the full team.
                if needs_agents and tickers and not selected_agents:
                    selected_agents = list(SPECIALIST_KEYS)
                # Can't research without a ticker.
                if not tickers:
                    needs_agents = False
                    selected_agents = []
        except asyncio.TimeoutError:
            logger.error("Supervisor planning timed out")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Supervisor planning failed: {e}")

    primary_ticker = tickers[0] if tickers else ""
    success_log = await log_agent_activity(
        message_id,
        "supervisor",
        f"Plan: tickers={tickers or 'none'}, agents={selected_agents or 'none'}, "
        f"market={market}, needs_research={needs_agents}",
    )
    await emit_chat_event(message_id, {"type": "agent-status", "node": "supervisor", "status": "completed"})

    return {
        "ticker": primary_ticker,
        "tickers": tickers,
        "market": market,
        "selected_agents": selected_agents,
        "needs_agents": needs_agents,
        "logs": [start_log, success_log],
    }


async def _run_specialist(state: AgentState, key: str) -> Dict[str, Any]:
    """Shared body for every slave node: run the agent for the primary ticker,
    capture its verdict, and emit status events. Only invoked when the master
    selected this specialist (see the conditional fan-out in graph.py)."""
    message_id = state["message_id"]
    ticker = state.get("ticker") or ""
    label = _LABELS.get(key, key)

    start_log = await log_agent_activity(message_id, key, f"{label} agent analysing {ticker}")
    await emit_chat_event(message_id, {"type": "agent-status", "node": key, "status": "running"})

    verdict_text = ""
    try:
        agent = SPECIALIST_AGENTS[key]()
        prompt = f"Analyse the stock ticker {ticker} for your specialism and give your verdict."
        result = await asyncio.wait_for(
            agent.ainvoke({"messages": [{"role": "user", "content": prompt}]}),
            timeout=_AGENT_TIMEOUT,
        )
        verdict_text = _last_message_text(result)
    except asyncio.TimeoutError:
        verdict_text = f"{label} analysis timed out."
    except Exception as e:  # noqa: BLE001
        verdict_text = f"{label} analysis unavailable ({e})."

    status = "completed" if verdict_text and "unavailable" not in verdict_text else "failed"
    done_log = await log_agent_activity(message_id, key, f"{label} agent verdict: {verdict_text[:200]}")
    await emit_chat_event(message_id, {"type": "agent-status", "node": key, "status": status})

    return {
        "findings": [{"agent": key, "label": label, "verdict": verdict_text}],
        "logs": [start_log, done_log],
    }


async def fundamentals_node(state: AgentState) -> Dict[str, Any]:
    return await _run_specialist(state, "fundamentals")


async def technical_node(state: AgentState) -> Dict[str, Any]:
    return await _run_specialist(state, "technical")


async def sentiment_node(state: AgentState) -> Dict[str, Any]:
    return await _run_specialist(state, "news_sentiment")


async def risk_node(state: AgentState) -> Dict[str, Any]:
    return await _run_specialist(state, "risk")
