from langgraph.graph import StateGraph, END
from backend.app.agents.state import AgentState
from backend.app.agents.nodes.research import research_node
from backend.app.agents.nodes.technical import technical_node
from backend.app.agents.nodes.news import news_node
from backend.app.agents.nodes.risk import risk_node
from backend.app.agents.nodes.decision import decision_node
from backend.app.agents.utils import log_agent_activity

async def init_node(state: AgentState):
    run_id = state["run_id"]
    ticker = state["ticker"]
    log = await log_agent_activity(
        run_id, 
        "orchestrator", 
        f"Launching Hedge Fund Multi-Agent System session for {ticker}."
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
