import json
import logging
import httpx
from datetime import datetime
from uuid import UUID
from typing import Dict, Any, List
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.models import AgentRun, InvestmentReport
from backend.app.agents.state import AgentState
from backend.app.agents.utils import log_agent_activity

logger = logging.getLogger("decision-node")


async def decision_node(state: AgentState) -> Dict[str, Any]:
    """Decision node synthesizing analysis streams, calling OpenAI (or fallback) for consensus memo, and saving results."""
    ticker = state["ticker"]
    run_id = state["run_id"]
    session_id = state["session_id"]

    quotes = state.get("quotes") or {}
    indicators = state.get("indicators") or {}
    sentiment = state.get("sentiment") or {}
    risk_metrics = state.get("risk_metrics") or {}
    sec_context = state.get("sec_context") or []

    start_log = await log_agent_activity(
        run_id,
        "decision",
        f"Consolidating all nodes data to compile consensus report for {ticker}..."
    )

    openai_key = settings.OPENAI_API_KEY
    if openai_key == "your_openai_key_here" or not openai_key:
        openai_key = None

    recommendation = "HOLD"
    confidence_score = 50
    content_markdown = ""
    source = "local_lexical_fallback"

    # Try OpenAI if key is present
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_key}"
            }

            prompt = (
                f"You are a Senior Investment Officer at a leading hedge fund. You must compile a comprehensive "
                f"investment research memo and decide on a final Buy/Hold/Sell recommendation with a confidence score (0-100).\n\n"
                f"Ticker symbol: {ticker}\n"
                f"Fundamental metrics: {quotes}\n"
                f"Technical Analysis metrics: {indicators}\n"
                f"Sentiment vectors: {sentiment}\n"
                f"Statistical Risk parameters: {risk_metrics}\n"
                f"Regulatory Risk footnotes context: {sec_context}\n\n"
                f"Generate a JSON object conforming exactly to this structure:\n"
                f"{{\n"
                f"  \"recommendation\": \"BUY\" | \"HOLD\" | \"SELL\",\n"
                f"  \"confidence_score\": <integer from 0 to 100>,\n"
                f"  \"memo_markdown\": <comprehensive multi-section markdown synthesis report detailing: "
                f"1. Executive Summary, 2. Financial Metrics Audit, 3. Technical Crossover analysis, "
                f"4. Sentiment and Catalyst narrative, 5. SEC footnote risk analysis and Statistical Beta risks. Use professional financial terminology.>\n"
                f"}}\n"
                f"Ensure response is valid JSON only."
            )

            payload = {
                "model": "gpt-4o-mini",
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You are a professional investment committee chatbot returning structured JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    result = resp.json()
                    content = json.loads(result["choices"][0]["message"]["content"])
                    recommendation = str(content.get("recommendation", "HOLD")).upper()
                    confidence_score = int(content.get("confidence_score", 50))
                    content_markdown = str(content.get("memo_markdown", ""))
                    source = "openai"
                    
                    # Track token budget usage
                    usage = result.get("usage", {})
                    total_tokens = usage.get("total_tokens", 0)
                    if total_tokens > 0:
                        try:
                            from backend.app.services.token_budget_service import token_budget_service
                            await token_budget_service.track_usage(session_id, total_tokens)
                        except Exception as tracking_err:
                            logger.error(f"Failed to record token usage: {tracking_err}")
                else:
                    logger.error(f"OpenAI decision fetch failed: {resp.text}")
        except Exception as e:
            logger.error(f"Error requesting OpenAI decision: {e}")

    # Fallback to local rule-based generation
    if not content_markdown:
        # 1. Compute quantitative recommendation score
        score = 50.0
        
        # Add Technical Score component
        ta_score = indicators.get("score", 0)
        score += ta_score * 0.2  # Max +20 / -20
        
        # Add Sentiment Score component
        sent_score = sentiment.get("score", 0)
        score += sent_score * 0.2  # Max +20 / -20
        
        # Add price change velocity
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

        # 2. Formulate Markdown template
        company_name = quotes.get("name", ticker)
        price = quotes.get("price", 0.0)
        sector = quotes.get("sector", "Technology")
        industry = quotes.get("industry", "Software")
        ta_rating = indicators.get("rating", "HOLD")
        sent_rating = sentiment.get("rating", "HOLD")
        sent_summary = sentiment.get("summary", "No news sentiment gathered.")
        vol = risk_metrics.get("annualized_volatility", 0.2) * 100

        # Build SEC citations
        sec_bullets = ""
        if sec_context:
            for i, chunk in enumerate(sec_context):
                text_slice = chunk["text"][:300] + "..."
                sec_bullets += f"\n* **Disclosure [{i+1}] ({chunk['section']})**: {text_slice}\n"
        else:
            sec_bullets = "\n* *No SEC 10-K filings context available in vector store.*"

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
* **Market Capitalization:** ${quotes.get('market_cap', 0.0):,.2f}M

---

## 3. Technical Posture Audit
Our Technical Indicators scoring pipeline registered a rating of **{ta_rating}** (Score: {ta_score}).
* **Key Oscillators & Trend Signals:**
  * RSI: {indicators.get('signals', {}).get('rsi', {}).get('signal', 'Neutral')}
  * MACD: {indicators.get('signals', {}).get('macd', {}).get('signal', 'Neutral')}
  * Bollinger Bands: {indicators.get('signals', {}).get('bollinger', {}).get('signal', 'Neutral')}
* **Classic Pivot Boundaries:**
  * Resistances: R2 = ${indicators.get('pivots', {}).get('r2', 0.0):.2f} | R1 = ${indicators.get('pivots', {}).get('r1', 0.0):.2f}
  * Supports: S1 = ${indicators.get('pivots', {}).get('s1', 0.0):.2f} | S2 = ${indicators.get('pivots', {}).get('s2', 0.0):.2f}

---

## 4. News & Social Sentiment Vector
News headlines and Reddit sentiment returned an aggregated rating of **{sent_rating}** (Score: {sent_score}).
* **Summary Catalyst Synthesis:**
  {sent_summary}
* **Identified Catalysts:**
  {" ".join(f"- {op}" for op in sentiment.get('opportunities', []))}
* **Identified Vulnerabilities:**
  {" ".join(f"- th" for th in sentiment.get('threats', []))}

---

## 5. Risk Footnotes & Volatility Metrics
* **Statistical Beta Coefficient:** {beta:.2f} (versus S&P 500 benchmark index)
* **Annualized Daily Volatility:** {vol:.2f}% (computed over {risk_metrics.get('history_days', 0)} trading days)
* **Indexed SEC 10-K Footnote Disclosures:**
  {sec_bullets}
"""

    # 3. Write execution reports to Postgres Database
    db_write_log = ""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Update AgentRun status
                stmt = select(AgentRun).where(AgentRun.id == UUID(run_id))
                result = await session.execute(stmt)
                agent_run = result.scalar_one_or_none()
                
                if agent_run:
                    agent_run.status = "completed"
                    agent_run.ended_at = datetime.utcnow()
                    
                    # Create InvestmentReport entry
                    report = InvestmentReport(
                        run_id=UUID(run_id),
                        ticker=ticker,
                        recommendation=recommendation.lower(),
                        confidence_score=confidence_score,
                        content_markdown=content_markdown
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
        f"Consensus report generated via {source}. Rating: {recommendation}. {db_write_log}"
    )

    return {
        "status": "completed",
        "decision": {
            "recommendation": recommendation,
            "confidence_score": confidence_score,
            "content_markdown": content_markdown
        },
        "logs": [start_log, success_log]
    }
