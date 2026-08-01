from typing import TypedDict, List, Dict, Any, Optional, Annotated

def append_logs(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Safe parallel reducer appending execution logs without overwriting."""
    if not left:
        left = []
    if not right:
        right = []
    return left + right

class AgentState(TypedDict):
    session_id: str
    ticker: str
    run_id: str
    status: str
    quotes: Dict[str, Any]
    indicators: Dict[str, Any]
    sentiment: Dict[str, Any]
    sec_context: List[Dict[str, Any]]
    risk_metrics: Dict[str, Any]
    decision: Dict[str, Any]
    logs: Annotated[List[Dict[str, Any]], append_logs]

    # Chat-graph-only fields (see agents/chat_nodes.py, agents/graph.py:create_chat_graph).
    # Unused by the original ticker-only graph (agents/graph.py:create_agent_graph).
    query: str
    message_id: str
    market: str  # "IN" | "US"
    intent: str  # "analysis" | "comparison" | "general_question"
    needs_agents: bool

    # Master/slave chat-graph fields (new agentic architecture):
    tickers: List[str]                # all tickers the master planned to analyse
    selected_agents: List[str]        # which specialist slaves the master dispatched
    portfolio_review: bool            # master decided the question is about the user's whole portfolio
    portfolio_context: str            # compact summary of the user's holdings, injected as agent context
    findings: Annotated[List[Dict[str, Any]], append_logs]  # each slave's verdict, appended in parallel
