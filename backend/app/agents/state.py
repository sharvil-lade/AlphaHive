from typing import Annotated, Any, TypedDict


def append_logs(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    quotes: dict[str, Any]
    indicators: dict[str, Any]
    sentiment: dict[str, Any]
    sec_context: list[dict[str, Any]]
    risk_metrics: dict[str, Any]
    decision: dict[str, Any]
    logs: Annotated[list[dict[str, Any]], append_logs]

    # Chat-graph-only fields (see agents/chat_nodes.py, agents/graph.py:create_chat_graph).
    # Unused by the original ticker-only graph (agents/graph.py:create_agent_graph).
    query: str
    message_id: str
    market: str  # "IN" | "US"
    intent: str  # "analysis" | "comparison" | "general_question"
    needs_agents: bool

    # Master/slave chat-graph fields (new agentic architecture):
    tickers: list[str]  # all tickers the master planned to analyse
    selected_agents: list[str]  # which specialist slaves the master dispatched
    portfolio_review: bool  # master decided the question is about the user's whole portfolio
    portfolio_context: str  # compact summary of the user's holdings, injected as agent context
    findings: Annotated[list[dict[str, Any]], append_logs]  # each slave's verdict, appended in parallel
