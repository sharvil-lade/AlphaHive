"""Agent definitions — the master/supervisor and the specialist slave agents.

This is the heart of the "proper agent" rework. Instead of hand-written functions
that fetch data in a fixed order, each specialist is a real
`langgraph.prebuilt.create_react_agent`: a tool-calling ReAct loop bound to a
focused set of API tools (see `app/agents/tools/`). The agent itself decides which
tools to call and when, reasons over the results, and returns its own verdict.

Topology (master–slave / supervisor–worker):

    master_supervisor            (has the portfolio tool + plans the work)
        ├── fundamentals_agent   (quote + profile tools)
        ├── technical_agent      (technical-analysis tool)
        ├── sentiment_agent      (news-sentiment tool)
        └── risk_agent           (risk-metrics + SEC-filing tools)

The master plans which slaves to dispatch for a given question (grounded in the
user's portfolio), the slaves run independently and report back, and the master
then synthesises the final decision (see `app/agents/graph.py`).

Agents are built lazily and cached so importing this module never requires a
configured LLM proxy.
"""

from functools import lru_cache
from typing import List, Literal

from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from app.agents.llm import get_chat_model
from app.agents.tools import (
    FUNDAMENTALS_TOOLS,
    PORTFOLIO_TOOLS,
    RISK_TOOLS,
    SENTIMENT_TOOLS,
    TECHNICAL_TOOLS,
)
from app.core.config import settings

# Canonical specialist keys — these MUST match the SSE `node` names the frontend
# AgentTracePanel renders, and the keys the supervisor plan selects from.
FUNDAMENTALS = "fundamentals"
TECHNICAL = "technical"
NEWS_SENTIMENT = "news_sentiment"
RISK = "risk"
SPECIALIST_KEYS = [FUNDAMENTALS, TECHNICAL, NEWS_SENTIMENT, RISK]


# ────────────────────────────── Master plan schema ──────────────────────────────

class SupervisorPlan(BaseModel):
    """Structured plan the master agent returns after reading the query + portfolio."""

    needs_research: bool = Field(
        description=(
            "True if answering well requires analysing one or more specific stocks. "
            "False for greetings, definitions, or general market questions a direct "
            "answer can handle."
        )
    )
    tickers: List[str] = Field(
        default_factory=list,
        description='Ticker symbols to analyse (e.g. ["RELIANCE"]). Empty if needs_research is false.',
    )
    market: Literal["IN", "US"] = Field(
        default="IN",
        description='"IN" for NSE/BSE-listed names, "US" otherwise. Default "IN".',
    )
    selected_agents: List[str] = Field(
        default_factory=list,
        description=(
            "Which specialist agents to dispatch, any subset of: "
            '"fundamentals", "technical", "news_sentiment", "risk". '
            "Empty if needs_research is false."
        ),
    )
    reasoning: str = Field(
        default="",
        description="One short sentence on why these agents/tickers were chosen.",
    )


# ────────────────────────────── Specialist prompts ──────────────────────────────

_FUNDAMENTALS_PROMPT = (
    "You are a fundamentals analyst on a stock research team. For the ticker you are "
    "given, use your tools to fetch the live quote and company profile, then judge the "
    "fundamentals. Respond with a short verdict in this exact form:\n"
    "RATING: BULLISH | NEUTRAL | BEARISH\nCONFIDENCE: <0-100>\n"
    "RATIONALE: <1-2 sentences grounded in the data you fetched>."
)

_TECHNICAL_PROMPT = (
    "You are a technical analyst on a stock research team. For the ticker you are "
    "given, use your technical-analysis tool to get indicators and the posture score, "
    "then give your read of momentum/trend. Respond with a short verdict in this exact "
    "form:\nRATING: BUY | HOLD | SELL\nCONFIDENCE: <0-100>\n"
    "RATIONALE: <1-2 sentences grounded in the indicators>."
)

_SENTIMENT_PROMPT = (
    "You are a news & sentiment analyst on a stock research team. For the ticker you "
    "are given, use your sentiment tool to read the current news/social narrative, then "
    "summarise it. Respond with a short verdict in this exact form:\n"
    "RATING: BUY | HOLD | SELL\nCONFIDENCE: <0-100>\n"
    "RATIONALE: <1-2 sentences on the narrative, key opportunities and threats>."
)

_RISK_PROMPT = (
    "You are a risk analyst on a stock research team. For the ticker you are given, use "
    "your tools to get statistical risk metrics (beta, volatility) and any SEC filing "
    "risk factors, then judge the risk. Respond with a short verdict in this exact "
    "form:\nRATING: LOW | MODERATE | HIGH\nCONFIDENCE: <0-100>\n"
    "RATIONALE: <1-2 sentences on beta, volatility, and disclosed risks>."
)

_SUPERVISOR_PROMPT = (
    "You are the master supervisor of a stock research team. Read the user's question "
    "and the summary of their portfolio provided in the conversation. If the question "
    "is about specific stock(s) and would benefit from research, plan which specialist "
    "agents to dispatch. You may call the get_user_portfolio tool if you need the "
    "user's live holdings to decide (e.g. 'should I rebalance my portfolio?'). "
    "Available specialists: fundamentals, technical, news_sentiment, risk. "
    "Prefer dispatching all four for a genuine buy/sell/hold decision on a single "
    "stock. For a pure definition, greeting, or broad market question, set "
    "needs_research to false and leave tickers/agents empty."
)


# ─────────────────────────────── Agent factories ────────────────────────────────

@lru_cache(maxsize=1)
def fundamentals_agent():
    return create_react_agent(
        get_chat_model(), FUNDAMENTALS_TOOLS, prompt=_FUNDAMENTALS_PROMPT, name="fundamentals_agent"
    )


@lru_cache(maxsize=1)
def technical_agent():
    return create_react_agent(
        get_chat_model(), TECHNICAL_TOOLS, prompt=_TECHNICAL_PROMPT, name="technical_agent"
    )


@lru_cache(maxsize=1)
def sentiment_agent():
    return create_react_agent(
        get_chat_model(), SENTIMENT_TOOLS, prompt=_SENTIMENT_PROMPT, name="sentiment_agent"
    )


@lru_cache(maxsize=1)
def risk_agent():
    return create_react_agent(
        get_chat_model(), RISK_TOOLS, prompt=_RISK_PROMPT, name="risk_agent"
    )


@lru_cache(maxsize=1)
def master_supervisor():
    """The master agent: portfolio-aware planner returning a structured SupervisorPlan."""
    return create_react_agent(
        get_chat_model(settings.LLM_MODEL_SYNTHESIS),
        PORTFOLIO_TOOLS,
        prompt=_SUPERVISOR_PROMPT,
        response_format=SupervisorPlan,
        name="master_supervisor",
    )


# Maps a specialist key -> its agent factory, so the graph can dispatch by name.
SPECIALIST_AGENTS = {
    FUNDAMENTALS: fundamentals_agent,
    TECHNICAL: technical_agent,
    NEWS_SENTIMENT: sentiment_agent,
    RISK: risk_agent,
}
