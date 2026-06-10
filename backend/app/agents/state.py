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
