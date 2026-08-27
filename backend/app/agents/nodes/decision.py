import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.agents.state import AgentState
from app.agents.utils import log_agent_activity
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.models import AgentRun, InvestmentReport
from app.services.llm_client import llm_client
from app.services.stock_service import stock_service

logger = logging.getLogger("decision-node")


async def decision_node(state: AgentState) -> dict[str, Any]:
    """Decision node synthesizing analysis streams, calling the LLM client (or local fallback) for consensus memo, and saving results."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    session_id = state["session_id"]

    quotes = state.get("quotes") or {}
    indicators = state.get("indicators") or {}
    sentiment = state.get("sentiment") or {}
    risk_metrics = state.get("risk_metrics") or {}
    sec_context = state.get("sec_context") or []

    start_log = await log_agent_activity(
        run_id, "decision", f"Consolidating all nodes data to compile consensus report for {ticker}..."
    )

    recommendation = "HOLD"
    confidence_score = 50
    content_markdown = ""
    source = "local_lexical_fallback"

    if llm_client.is_configured:
        fundamentals_verdict = quotes.get("agent_verdict") or {}
        technical_verdict = indicators.get("agent_verdict") or {}
        risk_verdict = risk_metrics.get("agent_verdict") or {}

        prompt = (
            f"You are a Senior Investment Officer at a leading hedge fund, chairing an investment committee. "
            f"Four independent specialist agents have each analyzed {ticker} on their own and reported back:\n"
            f"- Fundamentals Agent: {fundamentals_verdict.get('rating', 'n/a')} "
            f"(confidence {fundamentals_verdict.get('confidence', 'n/a')}%) — "
            f"{fundamentals_verdict.get('rationale', 'no rationale available')}\n"
            f"- Technical Agent: {technical_verdict.get('rating', indicators.get('rating', 'n/a'))} "
            f"(confidence {technical_verdict.get('confidence', 'n/a')}%) — "
            f"{technical_verdict.get('rationale', 'no rationale available')}\n"
            f"- News/Sentiment Agent: {sentiment.get('rating', 'n/a')} — "
            f"{sentiment.get('summary', 'no summary available')}\n"
            f"- Risk Agent: {risk_verdict.get('rating', 'n/a')} "
            f"(confidence {risk_verdict.get('confidence', 'n/a')}%) — "
            f"{risk_verdict.get('rationale', 'no rationale available')}\n\n"
            f"Weigh these four independent opinions against each other — note explicitly where they agree or "
            f"disagree — then compile a comprehensive investment research memo and decide on a final "
            f"Buy/Hold/Sell recommendation with a confidence score (0-100).\n\n"
            f"Ticker symbol: {ticker}\n"
            f"Fundamental metrics: {quotes}\n"
            f"Technical Analysis metrics: {indicators}\n"
            f"Sentiment vectors: {sentiment}\n"
            f"Statistical Risk parameters: {risk_metrics}\n"
            f"Regulatory Risk footnotes context: {sec_context}\n\n"
            f"Generate a JSON object conforming exactly to this structure:\n"
            f"{{\n"
            f'  "recommendation": "BUY" | "HOLD" | "SELL",\n'
            f'  "confidence_score": <integer from 0 to 100>,\n'
            f'  "memo_markdown": <comprehensive multi-section markdown synthesis report detailing: '
            f"1. Executive Summary, 2. Financial Metrics Audit, 3. Technical Crossover analysis, "
            f"4. Sentiment and Catalyst narrative, 5. SEC footnote risk analysis and Statistical Beta risks. Use professional financial terminology.>\n"
            f"}}\n"
            f"Ensure response is valid JSON only."
        )

        result = await llm_client.complete(
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional investment committee chatbot returning structured JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
            session_id=session_id,
            model=settings.LLM_MODEL_SYNTHESIS,
            # A full multi-section markdown memo takes longer to generate than a
            # short JSON verdict (the specialist agents' default 20s is too short here).
            timeout=75.0,
        )

        if result:
            try:
                content = json.loads(result.content)
                recommendation = str(content.get("recommendation", "HOLD")).upper()
                confidence_score = int(content.get("confidence_score", 50))
                content_markdown = str(content.get("memo_markdown", ""))
                source = f"llm:{result.model_used}"
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.error(f"Failed to parse LLM decision response: {e}")

    if not content_markdown:
        score = 50.0

        ta_score = indicators.get("score", 0)
        score += ta_score * 0.2  # Max +20 / -20

        sent_score = sentiment.get("score", 0)
        score += sent_score * 0.2  # Max +20 / -20

        pct_change = quotes.get("percent_change", 0.0)
        score += min(max(pct_change * 2.0, -10.0), 10.0)  # Max +10 / -10

        # Risk Multipliers
        beta = risk_metrics.get("beta", 1.0)
        if beta > 1.5:
            score -= 5.0
        elif beta < 0.8:
            score += 5.0

        confidence_score = int(min(max(score, 0.0), 100.0))

        if confidence_score >= 65:
            recommendation = "BUY"
        elif confidence_score <= 35:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        benchmark_label = "Nifty 50" if stock_service.resolve_market(ticker) == "IN" else "S&P 500"
        company_name = quotes.get("name", ticker)
        price = quotes.get("price", 0.0)
        sector = quotes.get("sector", "Technology")
        industry = quotes.get("industry", "Software")
        ta_rating = indicators.get("rating", "HOLD")
        sent_rating = sentiment.get("rating", "HOLD")
        sent_summary = sentiment.get("summary", "No news sentiment gathered.")
        vol = risk_metrics.get("annualized_volatility", 0.2) * 100

        sec_bullets = ""
        if sec_context:
            for i, chunk in enumerate(sec_context):
                text_slice = chunk["text"][:300] + "..."
                sec_bullets += f"\n* **Disclosure [{i + 1}] ({chunk['section']})**: {text_slice}\n"
        else:
            sec_bullets = "\n* *No SEC 10-K filing excerpts indexed for this ticker.*"

        content_markdown = f"""# Investment Analysis Memo: {company_name} ({ticker})

> **Investment Decision:** **{recommendation}**
> **Confidence Score:** {confidence_score}%
> **Analysis Source:** Local Quantitative Rule-Engine (Deterministic Fallback)

---

## 1. Executive Summary
This memorandum presents a synthesized financial and technical consensus rating for **{company_name}** ({ticker}). Our quantitative orchestrator has evaluated short-term indicators, medium-term news & social sentiment indexes, and long-term regulatory filings to arrive at a **{recommendation}** recommendation with a confidence score of **{confidence_score}%**.

---

## 2. Financial & Fundamental Profile
* **Asset Name:** {company_name}
* **Current Spot Price:** ${price:.2f}
* **Sector / Industry:** {sector} | {industry}
* **Market Capitalization:** ${quotes.get("market_cap", 0.0):,.2f}M

---

## 3. Technical Posture Audit
Our Technical Indicators scoring pipeline registered a rating of **{ta_rating}** (Score: {ta_score}).
* **Key Oscillators & Trend Signals:**
  * RSI: {indicators.get("signals", {}).get("rsi", {}).get("signal", "Neutral")}
  * MACD: {indicators.get("signals", {}).get("macd", {}).get("signal", "Neutral")}
  * Bollinger Bands: {indicators.get("signals", {}).get("bollinger", {}).get("signal", "Neutral")}
* **Classic Pivot Boundaries:**
  * Resistances: R2 = ${indicators.get("pivots", {}).get("r2", 0.0):.2f} | R1 = ${indicators.get("pivots", {}).get("r1", 0.0):.2f}
  * Supports: S1 = ${indicators.get("pivots", {}).get("s1", 0.0):.2f} | S2 = ${indicators.get("pivots", {}).get("s2", 0.0):.2f}

---

## 4. News & Social Sentiment Vector
News headlines and Reddit sentiment returned an aggregated rating of **{sent_rating}** (Score: {sent_score}).
* **Summary Catalyst Synthesis:**
  {sent_summary}
* **Identified Catalysts:**
  {" ".join(f"- {op}" for op in sentiment.get("opportunities", []))}
* **Identified Vulnerabilities:**
  {" ".join("- th" for th in sentiment.get("threats", []))}

---

## 5. Risk Footnotes & Volatility Metrics
* **Statistical Beta Coefficient:** {beta:.2f} (versus {benchmark_label} benchmark index)
* **Annualized Daily Volatility:** {vol:.2f}% (computed over {risk_metrics.get("history_days", 0)} trading days)
* **Indexed SEC 10-K Footnote Disclosures:**
  {sec_bullets}
"""

    db_write_log = ""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = select(AgentRun).where(AgentRun.id == UUID(run_id))
                result = await session.execute(stmt)
                agent_run = result.scalar_one_or_none()

                if agent_run:
                    agent_run.status = "completed"
                    agent_run.ended_at = datetime.utcnow()

                    report = InvestmentReport(
                        run_id=UUID(run_id),
                        ticker=ticker,
                        recommendation=recommendation.lower(),
                        confidence_score=confidence_score,
                        content_markdown=content_markdown,
                    )
                    session.add(report)
                    db_write_log = f"Successfully saved investment report row in PostgreSQL. ID: {report.id}"
                else:
                    db_write_log = "Warning: Could not find matching AgentRun database row to update."
    except Exception as e:
        db_write_log = f"PostgreSQL database commit failed: {e}."
        logger.error(f"Postgres database report write failure: {e}")

    success_log = await log_agent_activity(
        run_id,
        "decision",
        f"Consensus report generated via {source}. Rating: {recommendation}. {db_write_log}",
    )

    return {
        "status": "completed",
        "decision": {
            "recommendation": recommendation,
            "confidence_score": confidence_score,
            "content_markdown": content_markdown,
        },
        "logs": [start_log, success_log],
    }
