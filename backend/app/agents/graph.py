from langgraph.graph import END, StateGraph

from app.agents.chat_nodes import (
    bear_node,
    fundamentals_node,
    portfolio_doctor_node,
    supervisor_node,
)
from app.agents.chat_nodes import (
    risk_node as chat_risk_node,
)
from app.agents.chat_nodes import (
    sentiment_node as chat_sentiment_node,
)
from app.agents.chat_nodes import (
    technical_node as chat_technical_node,
)
from app.agents.nodes.decision import decision_node
from app.agents.nodes.news import news_node
from app.agents.nodes.research import research_node
from app.agents.nodes.risk import risk_node
from app.agents.nodes.synthesis import synthesis_node
from app.agents.nodes.technical import technical_node
from app.agents.state import AgentState
from app.agents.utils import log_agent_activity


async def init_node(state: AgentState):
    run_id = state["run_id"]
    ticker = state["ticker"]
    log = await log_agent_activity(
        run_id, "orchestrator", f"Launching AlphaHive Multi-Agent System session for {ticker}."
    )
    return {"status": "processing", "logs": [log]}


def create_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("init", init_node)
    workflow.add_node("research", research_node)
    workflow.add_node("technical", technical_node)
    workflow.add_node("news", news_node)
    workflow.add_node("risk", risk_node)
    workflow.add_node("decision", decision_node)

    workflow.set_entry_point("init")

    # Fork: Orchestrator splits to parallel analysis streams
    workflow.add_edge("init", "research")
    workflow.add_edge("init", "technical")
    workflow.add_edge("init", "news")
    workflow.add_edge("init", "risk")

    # Join: Parallel workers feed results into decision node
    workflow.add_edge("research", "decision")
    workflow.add_edge("technical", "decision")
    workflow.add_edge("news", "decision")
    workflow.add_edge("risk", "decision")

    workflow.add_edge("decision", END)

    return workflow.compile()


agent_graph = create_agent_graph()


# Per-stock analyst slaves the supervisor selects from (must match the plan's
# `selected_agents` keys and the SSE `node` names the frontend renders).
_PER_STOCK_ANALYSTS = ["fundamentals", "technical", "news_sentiment", "risk"]
# Every specialist node registered in the graph (analysts + auto-dispatched bear +
# portfolio doctor). All feed into synthesis.
_ALL_SPECIALIST_NODES = [*_PER_STOCK_ANALYSTS, "bear", "portfolio_doctor"]


def _route_after_supervisor(state: AgentState):
    """Master delegation: fan out to the per-stock analysts the supervisor selected
    (always adding the Bear red-team to challenge them), plus the Portfolio Doctor if
    it flagged a portfolio review. If nothing is needed, short-circuit to synthesis."""
    targets = []
    if state.get("needs_agents") and state.get("selected_agents"):
        targets += [n for n in state["selected_agents"] if n in _PER_STOCK_ANALYSTS]
        if targets:
            targets.append("bear")  # always red-team a genuine stock analysis
    # Only dispatch the Portfolio Doctor if the user actually has holdings — otherwise
    # it's a wasted call that can only report "your portfolio is empty".
    ctx = (state.get("portfolio_context") or "").lower()
    has_holdings = "empty" not in ctx and "no holdings" not in ctx and "could not be loaded" not in ctx
    if state.get("portfolio_review") and has_holdings:
        targets.append("portfolio_doctor")
    return targets or ["synthesis"]


def create_chat_graph():
    """Chat graph — master/slave (supervisor/worker) agentic architecture.

    free-form query
      -> supervisor (master):   portfolio-aware planner; picks tickers + which slaves
      -> [fundamentals | technical | news_sentiment | risk] (slaves, parallel):
             each a real create_react_agent that calls its own API tools
      -> synthesis (master):    streams the final, portfolio-aware decision

    Distinct from `create_agent_graph()` above (the original ticker-only memo flow,
    kept as-is and still reachable via POST /api/v1/agents/run) — this graph is
    driven by a natural-language `query`, and its synthesis node streams text +
    emits chat SSE events instead of writing to Postgres itself.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("fundamentals", fundamentals_node)
    workflow.add_node("technical", chat_technical_node)
    workflow.add_node("news_sentiment", chat_sentiment_node)
    workflow.add_node("risk", chat_risk_node)
    workflow.add_node("bear", bear_node)
    workflow.add_node("portfolio_doctor", portfolio_doctor_node)
    workflow.add_node("synthesis", synthesis_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        [*_ALL_SPECIALIST_NODES, "synthesis"],
    )

    for node in _ALL_SPECIALIST_NODES:
        workflow.add_edge(node, "synthesis")
    workflow.add_edge("synthesis", END)

    return workflow.compile()


chat_graph = create_chat_graph()
