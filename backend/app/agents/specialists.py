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
    RISK_TOOLS,
    SENTIMENT_TOOLS,
    TECHNICAL_TOOLS,
    get_risk_metrics,
    get_stock_quote,
    get_user_portfolio,
)
from app.core.config import settings

# Canonical specialist keys — these MUST match the SSE `node` names the frontend
# AgentTracePanel renders, and the keys the supervisor plan selects from.
FUNDAMENTALS = "fundamentals"
TECHNICAL = "technical"
NEWS_SENTIMENT = "news_sentiment"
RISK = "risk"
SPECIALIST_KEYS = [FUNDAMENTALS, TECHNICAL, NEWS_SENTIMENT, RISK]

# Portfolio Doctor is a portfolio-level specialist (no single ticker) — routed via
# the plan's `portfolio_review` flag rather than the per-ticker `selected_agents`.
PORTFOLIO_DOCTOR = "portfolio_doctor"

# The Bear/Red-Team agent is NOT selectable by the supervisor — it is auto-dispatched
# on every per-stock analysis to argue the opposite case and counter confirmation bias.
BEAR = "bear"


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
            "Which per-stock specialist agents to dispatch, any subset of: "
            '"fundamentals", "technical", "news_sentiment", "risk". '
            "Empty if needs_research is false."
        ),
    )
    portfolio_review: bool = Field(
        default=False,
        description=(
            "True if the question is about the user's OWN overall portfolio/holdings "
            "(e.g. 'analyse my portfolio', 'am I too concentrated?', 'how risky is my "
            "portfolio?', 'should I rebalance?', 'does adding X fit my portfolio?'). "
            "This dispatches the Portfolio Doctor agent. Can be true alongside per-stock "
            "agents when the user asks how a specific stock fits their portfolio."
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

_BEAR_PROMPT = (
    "You are the Bear — a deliberately skeptical red-team analyst on a stock research "
    "team. Your job is to build the strongest possible case AGAINST buying the ticker "
    "you are given, so the team doesn't fall for confirmation bias. Use your tools "
    "(quote, technicals, news sentiment, risk metrics, SEC filings) to find real red "
    "flags: stretched valuation, deteriorating technicals, negative catalysts, high "
    "beta/volatility, disclosed risks, or crowded/hyped positioning. Be intellectually "
    "honest — do not fabricate; if the bear case is genuinely weak, say so. Respond with "
    "a short verdict in this exact form:\n"
    "RATING: STRONG_BEAR | MILD_BEAR | BEAR_CASE_WEAK\nCONFIDENCE: <0-100>\n"
    "RATIONALE: <1-3 sentences with the most important concrete red flags you found>."
)

_PORTFOLIO_DOCTOR_PROMPT = (
    "You are a portfolio doctor — a specialist who diagnoses a retail investor's whole "
    "portfolio. Call get_user_portfolio with the session_id you are given to load their "
    "live holdings, value, sector weights, gain/loss, and portfolio beta. You may call "
    "get_stock_quote or get_risk_metrics on individual holdings if you need more detail. "
    "Then diagnose:\n"
    "- Concentration: any single holding or sector that is an outsized share of the portfolio\n"
    "- Diversification: sector/asset spread and notable gaps or overlaps\n"
    "- Risk: portfolio beta and volatility vs the market; which holdings drive the risk\n"
    "- Performance: overall and standout winners/losers\n"
    "Respond with a concise diagnosis followed by 2-4 concrete, actionable suggestions "
    "(e.g. trim an over-weight position, add diversification in a missing sector). Be "
    "specific and reference the actual holdings and numbers. If the portfolio is empty, "
    "say so and suggest the user add or import their holdings first."
)

_SUPERVISOR_PROMPT = (
    "You are the master supervisor of a stock research team. Read the user's question "
    "and the summary of their portfolio provided in the conversation. Plan the work:\n"
    "- If the question is about specific stock(s), set needs_research and pick which "
    "per-stock specialists to dispatch (fundamentals, technical, news_sentiment, risk). "
    "Prefer all four for a genuine buy/sell/hold decision on a single stock.\n"
    "- If the question is about the user's OWN overall portfolio (concentration, risk, "
    "diversification, rebalancing, or whether a stock fits their holdings), set "
    "portfolio_review to true to dispatch the Portfolio Doctor. Both can be true at "
    "once (e.g. 'should I add more Reliance to my portfolio?').\n"
    "- For a pure definition, greeting, or broad market question, set needs_research "
    "and portfolio_review to false and leave tickers/agents empty.\n"
    "You may call the get_user_portfolio tool if you need the user's live holdings to decide."
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
def bear_agent():
    """Red-team specialist: argues the bearish case for a ticker using the full research
    toolset. Auto-dispatched on every stock analysis (not supervisor-selectable)."""
    tools = [*FUNDAMENTALS_TOOLS, *TECHNICAL_TOOLS, *SENTIMENT_TOOLS, *RISK_TOOLS]
    return create_react_agent(get_chat_model(), tools, prompt=_BEAR_PROMPT, name="bear_agent")


@lru_cache(maxsize=1)
def portfolio_doctor_agent():
    """Portfolio-level specialist: diagnoses the user's whole portfolio. Runs on the
    stronger synthesis model since it reasons across many holdings at once."""
    return create_react_agent(
        get_chat_model(settings.LLM_MODEL_SYNTHESIS),
        [get_user_portfolio, get_stock_quote, get_risk_metrics],
        prompt=_PORTFOLIO_DOCTOR_PROMPT,
        name="portfolio_doctor_agent",
    )


@lru_cache(maxsize=1)
def master_supervisor():
    """The master planner: returns a SupervisorPlan directly via structured output.

    Deliberately NOT a create_react_agent: that prebuilt's internal
    `generate_structured_response` step issues a schema-as-tool call without a
    `tools=` param, which some LiteLLM/Anthropic setups reject (400
    UnsupportedParamsError). A direct `with_structured_output` call is the reliable
    path (verified against the live proxy). Planning is a lightweight classification,
    so it runs on the fast primary model, and the user's portfolio is already injected
    into the prompt — no live tool call is needed here.

    Returns a Runnable: `.ainvoke(messages)` -> SupervisorPlan.
    """
    return get_chat_model(settings.LLM_MODEL_PRIMARY, temperature=0.0).with_structured_output(
        SupervisorPlan
    )


# Maps a specialist key -> its agent factory, so the graph can dispatch by name.
# Includes `bear` (auto-dispatched red-team) even though it isn't in SPECIALIST_KEYS.
SPECIALIST_AGENTS = {
    FUNDAMENTALS: fundamentals_agent,
    TECHNICAL: technical_agent,
    NEWS_SENTIMENT: sentiment_agent,
    RISK: risk_agent,
    BEAR: bear_agent,
}
