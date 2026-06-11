from typing import Dict, Any
from backend.app.agents.state import AgentState
from backend.app.services.sentiment_service import sentiment_service
from backend.app.agents.utils import log_agent_activity

async def news_node(state: AgentState) -> Dict[str, Any]:
    """News node scraping Reddit and financial reports to compute sentiment matrices."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    
    start_log = await log_agent_activity(
        run_id, 
        "news", 
        f"Retrieving news and social mentions to run sentiment analysis for {ticker}"
    )
    
    try:
        sentiment = await sentiment_service.analyze_sentiment(ticker, session_id=state.get("session_id"))
        
        success_log = await log_agent_activity(
            run_id, 
            "news", 
            f"Sentiment computation finished for {ticker}. Rating: {sentiment.get('rating', 'HOLD')} (Score: {sentiment.get('score', 0)})"
        )
        
        return {
            "sentiment": sentiment,
            "logs": [start_log, success_log]
        }
    except Exception as e:
        error_log = await log_agent_activity(
            run_id, 
            "news", 
            f"Error during news sentiment analysis: {e}"
        )
        return {
            "logs": [start_log, error_log]
        }
