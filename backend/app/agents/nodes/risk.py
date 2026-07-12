from typing import Dict, Any, List
import numpy as np
from app.agents.state import AgentState
from app.services.vector_store import vector_store
from app.services.stock_service import stock_service
from app.agents.utils import log_agent_activity, emit_chat_event
from app.agents.verdict import get_agent_verdict

# Beta is computed against the locally-relevant benchmark index — Nifty 50 for
# Indian tickers (URL-encoded "^NSEI", verified live via Yahoo's chart API),
# S&P 500 (SPY) for everything else.
_INDIA_BENCHMARK_SYMBOL = "%5ENSEI"
_US_BENCHMARK_SYMBOL = "SPY"


async def risk_node(state: AgentState) -> Dict[str, Any]:
    """Risk node computing statistical volatility, beta, and retrieving SEC disclosures."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    message_id = state.get("message_id")

    start_log = await log_agent_activity(
        run_id,
        "risk",
        f"Retrieving SEC filings and historical prices to run risk audit for {ticker}"
    )
    if message_id:
        await emit_chat_event(message_id, {"type": "agent-status", "node": "risk", "status": "running"})

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
        
    # 2. Compute Volatility and Beta (benchmarked against Nifty 50 for Indian
    # tickers, S&P 500 for everything else)
    benchmark_symbol = (
        _INDIA_BENCHMARK_SYMBOL if stock_service.resolve_market(ticker) == "IN" else _US_BENCHMARK_SYMBOL
    )
    try:
        stock_history = await stock_service.fetch_history(ticker, range_str="1y")
        benchmark_history = await stock_service.fetch_history(benchmark_symbol, range_str="1y")

        if len(stock_history) > 10:
            stock_closes = [h["close"] for h in stock_history]
            stock_returns = np.diff(stock_closes) / stock_closes[:-1]
            daily_vol = np.std(stock_returns)
            annualized_vol = daily_vol * np.sqrt(252)

            risk_metrics["annualized_volatility"] = float(annualized_vol)
            risk_metrics["history_days"] = len(stock_history)

            stock_by_date = {h["date"]: h["close"] for h in stock_history}
            benchmark_by_date = {h["date"]: h["close"] for h in benchmark_history}
            common_dates = sorted(list(set(stock_by_date.keys()) & set(benchmark_by_date.keys())))

            if len(common_dates) > 10:
                aligned_stock = [stock_by_date[d] for d in common_dates]
                aligned_benchmark = [benchmark_by_date[d] for d in common_dates]

                stock_rets = np.diff(aligned_stock) / aligned_stock[:-1]
                benchmark_rets = np.diff(aligned_benchmark) / aligned_benchmark[:-1]

                cov = np.cov(stock_rets, benchmark_rets)[0][1]
                benchmark_var = np.var(benchmark_rets)
                beta = cov / benchmark_var if benchmark_var > 0 else 1.0
                risk_metrics["beta"] = float(beta)
            else:
                risk_metrics["beta"] = 1.0

        risk_summary = (
            f"Beta {risk_metrics['beta']:.2f} vs {benchmark_symbol}, annualized volatility "
            f"{risk_metrics['annualized_volatility']*100:.2f}% over {risk_metrics['history_days']} trading days. "
            f"SEC risk-factor excerpts: {[c['text'][:200] for c in sec_context] or 'none available'}."
        )
        verdict = await get_agent_verdict(
            role="a risk analyst",
            data_summary=risk_summary,
            rating_options='"LOW" | "MODERATE" | "HIGH"',
            session_id=state.get("session_id"),
        )
        risk_metrics["agent_verdict"] = verdict

        stat_log = await log_agent_activity(
            run_id,
            "risk",
            f"Computed statistical risk profile for {ticker} (vs {benchmark_symbol}). "
            f"Volatility: {risk_metrics['annualized_volatility']*100:.2f}%, Beta: {risk_metrics['beta']:.2f}. "
            f"Risk agent verdict: {verdict['rating']} ({verdict['confidence']}%)."
        )
        if message_id:
            await emit_chat_event(message_id, {"type": "agent-status", "node": "risk", "status": "completed"})
    except Exception as e:
        stat_log = await log_agent_activity(
            run_id,
            "risk",
            f"Failed to calculate statistical risk metrics: {e}"
        )
        if message_id:
            await emit_chat_event(message_id, {"type": "agent-status", "node": "risk", "status": "failed"})

    return {
        "sec_context": sec_context,
        "risk_metrics": risk_metrics,
        "logs": [start_log, sec_log, stat_log]
    }
