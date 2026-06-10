from typing import Dict, Any
from backend.app.agents.state import AgentState
from backend.app.services.indicators_service import indicators_service
from backend.app.services.ta_scoring import ta_scoring
from backend.app.services.stock_service import stock_service
from backend.app.agents.utils import log_agent_activity

async def technical_node(state: AgentState) -> Dict[str, Any]:
    """Technical node evaluating oscillator indicators and daily pivot ranges."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    
    start_log = await log_agent_activity(
        run_id, 
        "technical", 
        f"Starting technical indicators scoring analysis for {ticker}"
    )
    
    try:
        quote = await stock_service.fetch_quote(ticker)
        indicators = await indicators_service.calculate_indicators(ticker)
        
        if not indicators:
            raise ValueError(f"Could not compute indicator metrics for symbol {ticker}")
            
        posture = ta_scoring.evaluate_posture(indicators, quote)
        
        success_log = await log_agent_activity(
            run_id, 
            "technical", 
            f"Technical posture evaluation complete for {ticker}. Rating: {posture.get('rating', 'HOLD')} (Score: {posture.get('score', 0)})"
        )
        
        return {
            "indicators": posture,
            "logs": [start_log, success_log]
        }
    except Exception as e:
        error_log = await log_agent_activity(
            run_id, 
            "technical", 
            f"Error during technical analysis computation: {e}"
        )
        return {
            "logs": [start_log, error_log]
        }
