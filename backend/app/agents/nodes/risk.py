from typing import Dict, Any, List
import numpy as np
from backend.app.agents.state import AgentState
from backend.app.services.vector_store import vector_store
from backend.app.services.stock_service import stock_service
from backend.app.agents.utils import log_agent_activity

async def risk_node(state: AgentState) -> Dict[str, Any]:
    """Risk node computing statistical volatility, beta, and retrieving SEC disclosures."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    
    start_log = await log_agent_activity(
        run_id, 
        "risk", 
        f"Retrieving SEC filings and historical prices to run risk audit for {ticker}"
    )
    
    sec_context = []
    risk_metrics = {
        "beta": 1.0,
        "annualized_volatility": 0.0,
        "history_days": 0
    }
    
    # 1. Fetch SEC RAG context
    try:
        sec_query = "regulatory risk factors, competition, operational threats, liabilities"
        sec_results = await vector_store.search_chunks(ticker, sec_query, limit=3)
        for r in sec_results:
            sec_context.append({
                "text": r.get("text", ""),
                "section": r.get("section", "Risk Factors"),
                "score": r.get("score", 0.0)
            })
        sec_log = await log_agent_activity(
            run_id, 
            "risk", 
            f"Retrieved {len(sec_context)} relevant risk factor chunks from SEC vector indexing."
        )
    except Exception as e:
        sec_log = await log_agent_activity(
            run_id, 
            "risk", 
            f"SEC filings vector store retrieval bypassed or failed: {e}. Falling back to default risk disclosures."
        )
        
    # 2. Compute Volatility and Beta
    try:
        stock_history = await stock_service.fetch_history(ticker, range_str="1y")
        spy_history = await stock_service.fetch_history("SPY", range_str="1y")
        
        if len(stock_history) > 10:
            stock_closes = [h["close"] for h in stock_history]
            stock_returns = np.diff(stock_closes) / stock_closes[:-1]
            daily_vol = np.std(stock_returns)
            annualized_vol = daily_vol * np.sqrt(252)
            
            risk_metrics["annualized_volatility"] = float(annualized_vol)
            risk_metrics["history_days"] = len(stock_history)
            
            stock_by_date = {h["date"]: h["close"] for h in stock_history}
            spy_by_date = {h["date"]: h["close"] for h in spy_history}
            common_dates = sorted(list(set(stock_by_date.keys()) & set(spy_by_date.keys())))
            
            if len(common_dates) > 10:
                aligned_stock = [stock_by_date[d] for d in common_dates]
                aligned_spy = [spy_by_date[d] for d in common_dates]
                
                stock_rets = np.diff(aligned_stock) / aligned_stock[:-1]
                spy_rets = np.diff(aligned_spy) / aligned_spy[:-1]
                
                cov = np.cov(stock_rets, spy_rets)[0][1]
                spy_var = np.var(spy_rets)
                beta = cov / spy_var if spy_var > 0 else 1.0
                risk_metrics["beta"] = float(beta)
            else:
                risk_metrics["beta"] = 1.0
        
        stat_log = await log_agent_activity(
            run_id,
            "risk",
            f"Computed statistical risk profile for {ticker}. Volatility: {risk_metrics['annualized_volatility']*100:.2f}%, Beta: {risk_metrics['beta']:.2f}"
        )
    except Exception as e:
        stat_log = await log_agent_activity(
            run_id,
            "risk",
            f"Failed to calculate statistical risk metrics: {e}"
        )
        
    return {
        "sec_context": sec_context,
        "risk_metrics": risk_metrics,
        "logs": [start_log, sec_log, stat_log]
    }
