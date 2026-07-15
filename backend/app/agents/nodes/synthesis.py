import logging
from typing import Any, Dict

from app.core.config import settings
from app.agents.state import AgentState
from app.agents.utils import log_agent_activity, emit_chat_event
from app.services.llm_client import llm_client

logger = logging.getLogger("synthesis-node")


def _build_analysis_prompt(state: AgentState) -> str:
    """Master decision prompt: weigh every slave agent's verdict, grounded in the
    user's portfolio, and answer the question."""
    ticker = state.get("ticker") or ""
    findings = state.get("findings") or []
    portfolio_context = state.get("portfolio_context") or "The user's portfolio is empty."

    findings_block = "\n\n".join(
        f"**{f.get('label', f.get('agent', 'Agent'))} Agent:**\n{f.get('verdict', 'no verdict')}"
        for f in findings
    ) or "No specialist verdicts were produced."

    return (
        "You are the lead analyst on a stock research team. Your specialist agents each "
        f"independently analysed {ticker} and reported their verdicts below. The user asked:\n"
        f'"{state["query"]}"\n\n'
        f"--- The user's current portfolio (use this to make the advice personal) ---\n"
        f"{portfolio_context}\n\n"
        f"--- Specialist agent verdicts ---\n{findings_block}\n\n"
        "Weigh these independent verdicts against each other — note explicitly where they "
        "agree or disagree — and, where relevant, relate the answer to the user's actual "
        "holdings (concentration, overlap with what they own, position sizing). Write a "
        "clear, well-structured markdown response answering the user's question directly. "
        "Include a brief summary verdict (Buy/Hold/Sell-leaning) with confidence, then "
        "supporting detail. Professional but conversational — a few short sections, not a "
        "wall of boilerplate."
    )


def _build_general_prompt(state: AgentState) -> str:
    portfolio_context = state.get("portfolio_context") or ""
    portfolio_note = (
        f"\n\nFor context, the user's portfolio is:\n{portfolio_context}"
        if portfolio_context and "empty" not in portfolio_context.lower()
        else ""
    )
    return (
        "You are AlphaHive, a helpful stock market research assistant focused on Indian and "
        "global equity markets. Answer the user's message directly and conversationally in "
        "markdown. If the message isn't really about a specific stock, just answer it "
        "helpfully — don't force a buy/hold/sell verdict."
        f"{portfolio_note}\n\n"
        f'User message: "{state["query"]}"'
    )


def _local_fallback_markdown(state: AgentState) -> str:
    """Deterministic fallback if no LLM is reachable."""
    ticker = state.get("ticker") or ""
    findings = state.get("findings") or []
    if not ticker or not findings:
        return (
            "I can share general market information, but I don't have a live LLM connection "
            "configured right now to answer open-ended questions in depth. Ask me about a "
            'specific stock (e.g. "Should I buy Reliance?") for a data-driven analysis.'
        )
    bullets = "\n".join(f"- **{f.get('label')}**: {f.get('verdict', '')[:200]}" for f in findings)
    return (
        f"## {ticker} — Specialist Read (No-LLM Fallback)\n\n{bullets}\n\n"
        "_No LLM was reachable for a full narrative synthesis — this is the raw specialist output._"
    )


async def synthesis_node(state: AgentState) -> Dict[str, Any]:
    """Final node in the chat graph: streams the synthesized answer to the client
    via chat SSE events, then returns the full content for persistence by the
    chat endpoint layer (this node never writes to Postgres itself)."""
    message_id = state["message_id"]
    session_id = state.get("session_id")

    start_log = await log_agent_activity(message_id, "synthesis", "Synthesizing final decision...")
    await emit_chat_event(message_id, {"type": "agent-status", "node": "synthesis", "status": "running"})

    ticker = state.get("ticker") or ""
    needs_agents = state.get("needs_agents", False)
    has_findings = bool(state.get("findings"))

    full_content = ""
    source = "local_fallback"

    if llm_client.is_configured:
        use_analysis = ticker and needs_agents and has_findings
        prompt = _build_analysis_prompt(state) if use_analysis else _build_general_prompt(state)
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
    success_log = await log_agent_activity(message_id, "synthesis", f"Decision synthesized via {source}.")

    return {
        "decision": {"content_markdown": full_content, "source": source},
        "logs": [start_log, success_log],
    }
