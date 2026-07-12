from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes.research import research_node
from app.agents.nodes.technical import technical_node
from app.agents.nodes.news import news_node
from app.agents.nodes.risk import risk_node
from app.agents.nodes.decision import decision_node
from app.agents.nodes.router import router_node
from app.agents.nodes.synthesis import synthesis_node
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


def _route_after_router(state: AgentState):
    """Fan out to all 4 specialists in parallel if the query needs a full analysis,
    otherwise short-circuit straight to synthesis (cheap path for general chat)."""
    if state.get("needs_agents"):
        return ["research", "technical", "news", "risk"]
    return ["synthesis"]


def create_chat_graph():
    """Chat graph: free-form query -> router (extracts tickers/intent) -> parallel
    specialist fan-out (only if needed) -> synthesis (streams the final answer).

    Distinct from `create_agent_graph()` above (the original ticker-only flow, kept
    as-is and still reachable via POST /api/v1/agents/run) — this graph is driven by
    a natural-language `query` instead of a pre-selected `ticker`, and its synthesis
    node streams text + emits chat SSE events instead of writing to Postgres itself.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("research", research_node)
    workflow.add_node("technical", technical_node)
    workflow.add_node("news", news_node)
    workflow.add_node("risk", risk_node)
    workflow.add_node("synthesis", synthesis_node)

    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router", _route_after_router, ["research", "technical", "news", "risk", "synthesis"]
    )

    workflow.add_edge("research", "synthesis")
    workflow.add_edge("technical", "synthesis")
    workflow.add_edge("news", "synthesis")
    workflow.add_edge("risk", "synthesis")
    workflow.add_edge("synthesis", END)

    return workflow.compile()


chat_graph = create_chat_graph()
