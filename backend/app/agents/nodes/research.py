from typing import Dict, Any
from backend.app.agents.state import AgentState
from backend.app.services.stock_service import stock_service
from backend.app.agents.utils import log_agent_activity

async def research_node(state: AgentState) -> Dict[str, Any]:
    """Research node gathering fundamental metrics and quote profiles."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    
    start_log = await log_agent_activity(
        run_id, 
        "research", 
        f"Initializing fundamental research for ticker: {ticker}"
    )
    
    try:
        quote = await stock_service.fetch_quote(ticker)
        profile = await stock_service.fetch_profile(ticker)
        
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
        
        success_log = await log_agent_activity(
            run_id, 
            "research", 
            f"Successfully gathered fundamental data for {ticker}. Name: {quotes_data['name']}, Price: ${quotes_data['price']}"
        )
        
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
        return {
            "logs": [start_log, error_log]
        }
