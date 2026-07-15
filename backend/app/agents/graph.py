from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes.research import research_node
from app.agents.nodes.technical import technical_node
from app.agents.nodes.news import news_node
from app.agents.nodes.risk import risk_node
from app.agents.nodes.decision import decision_node
from app.agents.nodes.synthesis import synthesis_node
from app.agents.chat_nodes import (
    supervisor_node,
    fundamentals_node,
    technical_node as chat_technical_node,
    sentiment_node as chat_sentiment_node,
    risk_node as chat_risk_node,
)
from app.agents.utils import log_agent_activity

async def init_node(state: AgentState):
    run_id = state["run_id"]
    ticker = state["ticker"]
    log = await log_agent_activity(
        run_id, 
        "orchestrator", 
        f"Launching AlphaHive Multi-Agent System session for {ticker}."
    )
    return {
        "status": "processing",
        "logs": [log]
    }

def create_agent_graph():
    # Initialize StateGraph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("init", init_node)
    workflow.add_node("research", research_node)
    workflow.add_node("technical", technical_node)
    workflow.add_node("news", news_node)
    workflow.add_node("risk", risk_node)
    workflow.add_node("decision", decision_node)
    
    # Entry point
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
    
    # Close graph
    workflow.add_edge("decision", END)
    
    return workflow.compile()

agent_graph = create_agent_graph()


# Node names for the chat graph's specialist slaves. These MUST match both the
# supervisor plan's `selected_agents` keys and the SSE `node` names the frontend
# AgentTracePanel renders.
_CHAT_SPECIALIST_NODES = ["fundamentals", "technical", "news_sentiment", "risk"]


def _route_after_supervisor(state: AgentState):
    """Master delegation: fan out only to the specialist slaves the supervisor
    selected. If it decided no research is needed (general question / no ticker),
    short-circuit straight to synthesis."""
    selected = state.get("selected_agents") or []
    if state.get("needs_agents") and selected:
        return [n for n in selected if n in _CHAT_SPECIALIST_NODES] or ["synthesis"]
    return ["synthesis"]


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
    workflow.add_node("synthesis", synthesis_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        [*_CHAT_SPECIALIST_NODES, "synthesis"],
    )

    for node in _CHAT_SPECIALIST_NODES:
        workflow.add_edge(node, "synthesis")
    workflow.add_edge("synthesis", END)

    return workflow.compile()


chat_graph = create_chat_graph()
