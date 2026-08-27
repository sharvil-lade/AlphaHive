from typing import Any

from app.agents.state import AgentState
from app.agents.utils import emit_chat_event, log_agent_activity
from app.services.sentiment_service import sentiment_service


async def news_node(state: AgentState) -> dict[str, Any]:
    """News/sentiment node aggregating headlines to compute sentiment matrices."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    message_id = state.get("message_id")

    start_log = await log_agent_activity(
        run_id, "news", f"Retrieving news and social mentions to run sentiment analysis for {ticker}"
    )
    if message_id:
        await emit_chat_event(
            message_id, {"type": "agent-status", "node": "news_sentiment", "status": "running"}
        )

    try:
        sentiment = await sentiment_service.analyze_sentiment(ticker, session_id=state.get("session_id"))

        success_log = await log_agent_activity(
            run_id,
            "news",
            f"Sentiment computation finished for {ticker}. Rating: {sentiment.get('rating', 'HOLD')} (Score: {sentiment.get('score', 0)})",
        )
        if message_id:
            await emit_chat_event(
                message_id, {"type": "agent-status", "node": "news_sentiment", "status": "completed"}
            )

        return {"sentiment": sentiment, "logs": [start_log, success_log]}
    except Exception as e:
        error_log = await log_agent_activity(run_id, "news", f"Error during news sentiment analysis: {e}")
        if message_id:
            await emit_chat_event(
                message_id, {"type": "agent-status", "node": "news_sentiment", "status": "failed"}
            )
        return {"logs": [start_log, error_log]}
