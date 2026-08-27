from typing import Any

from app.agents.state import AgentState
from app.agents.utils import emit_chat_event, log_agent_activity
from app.agents.verdict import get_agent_verdict
from app.services.indicators_service import indicators_service
from app.services.stock_service import stock_service
from app.services.ta_scoring import ta_scoring


async def technical_node(state: AgentState) -> dict[str, Any]:
    """Technical node evaluating oscillator indicators and daily pivot ranges, then
    having an independent technical-analyst agent explain/confirm the deterministic
    quant rating rather than just reporting the raw score (see agents/verdict.py)."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    message_id = state.get("message_id")

    start_log = await log_agent_activity(
        run_id, "technical", f"Starting technical indicators scoring analysis for {ticker}"
    )
    if message_id:
        await emit_chat_event(message_id, {"type": "agent-status", "node": "technical", "status": "running"})

    try:
        quote = await stock_service.fetch_quote(ticker) or {}
        indicators = await indicators_service.calculate_indicators(ticker)

        if not indicators:
            raise ValueError(f"Could not compute indicator metrics for symbol {ticker}")

        posture = ta_scoring.evaluate_posture(indicators, quote)

        verdict = await get_agent_verdict(
            role="a technical analyst",
            data_summary=(
                f"Quantitative technical score for {ticker}: {posture.get('score', 0)} "
                f"({posture.get('rating', 'HOLD')}). Signal breakdown: {posture.get('signals', {})}."
            ),
            rating_options='"BUY" | "HOLD" | "SELL"',
            session_id=state.get("session_id"),
            anchor_rating=posture.get("rating"),
        )
        posture["agent_verdict"] = verdict

        success_log = await log_agent_activity(
            run_id,
            "technical",
            f"Technical posture evaluation complete for {ticker}. Rating: {posture.get('rating', 'HOLD')} "
            f"(Score: {posture.get('score', 0)}). Technical agent verdict: {verdict['rating']} "
            f"({verdict['confidence']}%).",
        )
        if message_id:
            await emit_chat_event(
                message_id, {"type": "agent-status", "node": "technical", "status": "completed"}
            )

        return {"indicators": posture, "logs": [start_log, success_log]}
    except Exception as e:
        error_log = await log_agent_activity(
            run_id, "technical", f"Error during technical analysis computation: {e}"
        )
        if message_id:
            await emit_chat_event(
                message_id, {"type": "agent-status", "node": "technical", "status": "failed"}
            )
        return {"logs": [start_log, error_log]}
