import logging
from typing import Any

from app.agents.state import AgentState
from app.agents.utils import emit_chat_event, log_agent_activity
from app.core.config import settings
from app.services.llm_client import llm_client

logger = logging.getLogger("synthesis-node")


def _build_analysis_prompt(state: AgentState) -> str:
    """Master decision prompt: weigh every slave agent's verdict, grounded in the
    user's portfolio, and answer the question."""
    ticker = state.get("ticker") or ""
    findings = state.get("findings") or []
    portfolio_context = state.get("portfolio_context") or "The user's portfolio is empty."

    ok_findings = [f for f in findings if f.get("ok", True)]
    failed = [f.get("label", f.get("agent", "Agent")) for f in findings if not f.get("ok", True)]

    findings_block = (
        "\n\n".join(
            f"**{f.get('label', f.get('agent', 'Agent'))} Agent:**\n{f.get('verdict', 'no verdict')}"
            for f in ok_findings
        )
        or "No specialist verdicts were produced (their data sources were unavailable)."
    )

    gap_note = (
        f"\n\nNote: the {', '.join(failed)} agent(s) could not complete (data unavailable). "
        "Acknowledge this data gap honestly in your answer and lower your confidence "
        "accordingly rather than pretending you had full coverage."
        if failed
        else ""
    )

    subject = f"analysed {ticker}" if ticker else "reviewed the user's portfolio"

    return (
        "You are the lead analyst on a stock research team. Your specialist agents each "
        f"independently {subject} and reported below. The user asked:\n"
        f'"{state["query"]}"\n\n'
        f"--- The user's current portfolio (use this to make the advice personal) ---\n"
        f"{portfolio_context}\n\n"
        f"--- Specialist agent findings ---\n{findings_block}{gap_note}\n\n"
        "Weigh these independent findings against each other. One of them is the Bear "
        "(red-team) agent arguing the counter-case — take it seriously: explicitly weigh "
        "the bull case (the other analysts) against the Bear's case and note where the "
        "team agrees or disagrees, rather than glossing over the disagreement. Relate the "
        "answer to the user's actual holdings (concentration, overlap with what they own, "
        "position sizing). Write a clear, well-structured markdown response answering the "
        "user's question directly. Where a buy/hold/sell stance is relevant, give a brief "
        "summary verdict with confidence AND a short 'Bull vs Bear' contrast; for a "
        "portfolio review, lead with the diagnosis and concrete next actions. Professional "
        "but conversational — a few short sections, not a wall of boilerplate."
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
    if not findings:
        return (
            "I can share general market information, but I don't have a live LLM connection "
            "configured right now to answer open-ended questions in depth. Ask me about a "
            'specific stock (e.g. "Should I buy Reliance?") for a data-driven analysis.'
        )
    heading = f"{ticker} — Specialist Read" if ticker else "Portfolio Review"
    bullets = "\n".join(f"- **{f.get('label')}**: {f.get('verdict', '')[:200]}" for f in findings)
    return (
        f"## {heading} (No-LLM Fallback)\n\n{bullets}\n\n"
        "_No LLM was reachable for a full narrative synthesis — this is the raw specialist output._"
    )


async def synthesis_node(state: AgentState) -> dict[str, Any]:
    """Final node in the chat graph: streams the synthesized answer to the client
    via chat SSE events, then returns the full content for persistence by the
    chat endpoint layer (this node never writes to Postgres itself)."""
    message_id = state["message_id"]
    session_id = state.get("session_id")

    start_log = await log_agent_activity(message_id, "synthesis", "Synthesizing final decision...")
    await emit_chat_event(message_id, {"type": "agent-status", "node": "synthesis", "status": "running"})

    ticker = state.get("ticker") or ""
    needs_agents = state.get("needs_agents", False)
    portfolio_review = state.get("portfolio_review", False)
    has_findings = bool(state.get("findings"))

    full_content = ""
    source = "local_fallback"

    if llm_client.is_configured:
        use_analysis = has_findings and ((ticker and needs_agents) or portfolio_review)
        prompt = _build_analysis_prompt(state) if use_analysis else _build_general_prompt(state)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are AlphaHive, a stock market research assistant — an educational research "
                    "tool, NOT a SEBI-registered investment adviser. Frame conclusions as research and "
                    "reasoning the user should verify, not as personalised financial advice or a "
                    "guarantee; never promise returns. Format responses in GitHub-flavored markdown. "
                    "When showing a formula or calculation (e.g. P/E ratio, CAGR, beta), write it as "
                    "LaTeX using $$...$$ for a standalone equation or $...$ for an inline one — never as "
                    "plain-text fractions or ASCII math. Use markdown tables for side-by-side "
                    "comparisons and fenced code blocks for structured/tabular data."
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
