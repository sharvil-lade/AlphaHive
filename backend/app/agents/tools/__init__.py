"""Tool layer for the agentic chat system.

Every external data API the agents can reach is exposed here as a LangChain
`@tool`. This is the extension point the product is built around: to give an
agent a new capability, write a `@tool` function that wraps the API/service and
add it to that agent's tool list in `app/agents/specialists.py`. Nothing else
changes — the react agent discovers the new tool automatically.

Tools are grouped by the specialist that owns them so the mapping
"which agent gets which tools" stays obvious:

    FUNDAMENTALS_TOOLS  -> get_stock_quote, get_company_profile
    TECHNICAL_TOOLS     -> get_technical_analysis
    SENTIMENT_TOOLS     -> get_news_sentiment
    RISK_TOOLS          -> get_risk_metrics, search_sec_filings
    PORTFOLIO_TOOLS     -> get_user_portfolio   (master/supervisor context)
"""

from app.agents.tools.market_tools import get_company_profile, get_stock_quote
from app.agents.tools.portfolio_tools import get_user_portfolio
from app.agents.tools.risk_tools import get_risk_metrics, search_sec_filings
from app.agents.tools.sentiment_tools import get_news_sentiment
from app.agents.tools.technical_tools import get_technical_analysis

FUNDAMENTALS_TOOLS = [get_stock_quote, get_company_profile]
TECHNICAL_TOOLS = [get_technical_analysis]
SENTIMENT_TOOLS = [get_news_sentiment]
RISK_TOOLS = [get_risk_metrics, search_sec_filings]
PORTFOLIO_TOOLS = [get_user_portfolio]

# Flat registry — handy for introspection / future dynamic tool assignment.
ALL_TOOLS = [
    *FUNDAMENTALS_TOOLS,
    *TECHNICAL_TOOLS,
    *SENTIMENT_TOOLS,
    *RISK_TOOLS,
    *PORTFOLIO_TOOLS,
]

__all__ = [
    "get_stock_quote",
    "get_company_profile",
    "get_technical_analysis",
    "get_news_sentiment",
    "get_risk_metrics",
    "search_sec_filings",
    "get_user_portfolio",
    "FUNDAMENTALS_TOOLS",
    "TECHNICAL_TOOLS",
    "SENTIMENT_TOOLS",
    "RISK_TOOLS",
    "PORTFOLIO_TOOLS",
    "ALL_TOOLS",
]
