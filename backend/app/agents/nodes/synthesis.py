import logging
from typing import Any, Dict

from app.core.config import settings
from app.agents.state import AgentState
from app.agents.utils import log_agent_activity, emit_chat_event
from app.services.llm_client import llm_client

logger = logging.getLogger("synthesis-node")


def _build_analysis_prompt(state: AgentState) -> str:
    ticker = state.get("ticker") or ""
    quotes = state.get("quotes") or {}
    indicators = state.get("indicators") or {}
    sentiment = state.get("sentiment") or {}
    risk_metrics = state.get("risk_metrics") or {}
    sec_context = state.get("sec_context") or []

    fundamentals_verdict = quotes.get("agent_verdict") or {}
    technical_verdict = indicators.get("agent_verdict") or {}
    risk_verdict = risk_metrics.get("agent_verdict") or {}

    sec_bullets = "\n".join(
        f"- ({c.get('section', 'Risk Factors')}): {c.get('text', '')[:300]}" for c in sec_context
    ) or "No SEC filing context available."

    return (
        "You are the lead analyst on a stock research team. Four independent specialist agents have "
        f"each analyzed {ticker} on their own and reported back their read of the data. The user asked:\n"
        f'"{state["query"]}"\n\n'
        f"**Fundamentals Agent** — {fundamentals_verdict.get('rating', 'n/a')} "
        f"(confidence {fundamentals_verdict.get('confidence', 'n/a')}%): "
        f"{fundamentals_verdict.get('rationale', 'no rationale available')}\n"
        f"Raw data: {quotes}\n\n"
        f"**Technical Agent** — {technical_verdict.get('rating', indicators.get('rating', 'n/a'))} "
        f"(confidence {technical_verdict.get('confidence', 'n/a')}%): "
        f"{technical_verdict.get('rationale', 'no rationale available')}\n"
        f"Raw data: {indicators}\n\n"
        f"**News/Sentiment Agent** — {sentiment.get('rating', 'n/a')}: "
        f"{sentiment.get('summary', 'no summary available')}\n\n"
        f"**Risk Agent** — {risk_verdict.get('rating', 'n/a')} "
        f"(confidence {risk_verdict.get('confidence', 'n/a')}%): "
        f"{risk_verdict.get('rationale', 'no rationale available')}\n"
        f"Raw data: {risk_metrics}\n"
        f"SEC risk disclosures:\n{sec_bullets}\n\n"
        "Weigh these four independent opinions against each other — note explicitly where they agree or "
        "disagree — and write a clear, well-structured markdown response answering the user's question "
        "directly. Include a brief summary verdict (Buy/Hold/Sell-leaning) with confidence, then supporting "
        "detail. Use a professional but conversational tone, not a rigid template. Keep it focused — a few "
        "short sections, not a wall of boilerplate."
    )


def _build_general_prompt(state: AgentState) -> str:
    return (
        "You are AlphaHive, a helpful stock market research assistant focused on Indian and global "
        "equity markets. Answer the user's message directly and conversationally in markdown. If the "
        "message isn't really about a specific stock, just answer it helpfully — don't force a "
        "buy/hold/sell verdict.\n\n"
        f'User message: "{state["query"]}"'
    )


def _local_fallback_markdown(state: AgentState) -> str:
    """Deterministic fallback if no LLM is reachable — mirrors decision.py's rule-based
    scoring, adapted for the lighter chat context."""
    ticker = state.get("ticker") or ""
    if not ticker:
        return (
            "I can share general market information, but I don't have a live LLM connection "
            "configured right now to answer open-ended questions in depth. Ask me about a specific "
            'stock (e.g. "Should I buy Reliance?") for a data-driven analysis.'
        )

    indicators = state.get("indicators") or {}
    sentiment = state.get("sentiment") or {}
    risk_metrics = state.get("risk_metrics") or {}
    quotes = state.get("quotes") or {}

    score = 50.0
    score += indicators.get("score", 0) * 0.2
    score += sentiment.get("score", 0) * 0.2
    pct_change = quotes.get("percent_change", 0.0)
    score += min(max(pct_change * 2.0, -10.0), 10.0)
    beta = risk_metrics.get("beta", 1.0)
    if beta > 1.5:
        score -= 5.0
    elif beta < 0.8:
        score += 5.0
    confidence = int(min(max(score, 0.0), 100.0))
    recommendation = "BUY" if confidence >= 65 else "SELL" if confidence <= 35 else "HOLD"
    vol = risk_metrics.get("annualized_volatility", 0.0) * 100

    return (
        f"## {ticker} — Quick Take (Deterministic Fallback)\n\n"
        f"**Recommendation: {recommendation}** (confidence {confidence}%)\n\n"
        f"- Price: {quotes.get('price', 'n/a')} ({quotes.get('percent_change', 0):.2f}% today)\n"
        f"- Technical rating: {indicators.get('rating', 'HOLD')} (score {indicators.get('score', 0)})\n"
        f"- Sentiment rating: {sentiment.get('rating', 'HOLD')} (score {sentiment.get('score', 0)})\n"
        f"- Beta: {beta:.2f}, annualized volatility: {vol:.2f}%\n\n"
        "_This is a deterministic quantitative fallback — no LLM was reachable for a full narrative synthesis._"
    )


async def synthesis_node(state: AgentState) -> Dict[str, Any]:
    """Final node in the chat graph: streams the synthesized answer to the client
    via chat SSE events, then returns the full content for persistence by the
    chat endpoint layer (this node never writes to Postgres itself)."""
    message_id = state["message_id"]
    session_id = state.get("session_id")

    start_log = await log_agent_activity(message_id, "synthesis", "Synthesizing final response...")
    await emit_chat_event(message_id, {"type": "agent-status", "node": "synthesis", "status": "running"})

    ticker = state.get("ticker") or ""
    needs_agents = state.get("needs_agents", False)

    full_content = ""
    source = "local_fallback"

    if llm_client.is_configured:
        prompt = _build_analysis_prompt(state) if (ticker and needs_agents) else _build_general_prompt(state)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are AlphaHive, a stock market research assistant. Format responses in GitHub-"
                    "flavored markdown. When showing a formula or calculation (e.g. P/E ratio, CAGR, "
                    "beta), write it as LaTeX using $$...$$ for a standalone equation or $...$ for an "
                    "inline one — never as plain-text fractions or ASCII math. Use markdown tables for "
                    "side-by-side comparisons and fenced code blocks for structured/tabular data."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        async for delta in llm_client.stream(
            messages, session_id=session_id, model=settings.LLM_MODEL_SYNTHESIS, timeout=90.0
        ):
            full_content += delta
            await emit_chat_event(message_id, {"type": "text-delta", "delta": delta})
        if full_content.strip():
            source = f"llm:{settings.LLM_MODEL_SYNTHESIS}"

    if not full_content.strip():
        full_content = _local_fallback_markdown(state)
        # Stream the fallback as one chunk so the client still sees text arrive.
        await emit_chat_event(message_id, {"type": "text-delta", "delta": full_content})

    await emit_chat_event(message_id, {"type": "agent-status", "node": "synthesis", "status": "completed"})
    success_log = await log_agent_activity(message_id, "synthesis", f"Response synthesized via {source}.")

    return {
        "decision": {"content_markdown": full_content, "source": source},
        "logs": [start_log, success_log],
    }
