import json
import logging
from typing import Any

from app.services.llm_client import llm_client
from app.services.news_service import news_service
from app.services.social_scraper import social_scraper

logger = logging.getLogger("sentiment-service")


class SentimentService:
    """Service to evaluate news & social sentiment using the shared LLM client, or a local lexical fallback."""

    async def analyze_sentiment(self, symbol: str, session_id: str | None = None) -> dict[str, Any]:
        """Aggregate news articles and social mentions, then evaluate the unified sentiment score and summary."""
        symbol = symbol.upper()

        news_items = await news_service.fetch_news(symbol)
        reddit_posts = await social_scraper.fetch_reddit_posts(symbol)

        headlines = [item.get("headline", "") for item in news_items if item.get("headline")]
        social_texts = [f"{post.get('title', '')} - {post.get('text', '')}" for post in reddit_posts]

        combined_text = "\n".join(headlines + social_texts)

        if llm_client.is_configured:
            llm_sentiment = await self._fetch_llm_sentiment(symbol, headlines, social_texts, session_id)
            if llm_sentiment:
                return llm_sentiment

        # No proxy, or the call failed: fall back to the local lexical analyser.
        return self._evaluate_local_sentiment(symbol, headlines, social_texts, combined_text)

    async def _fetch_llm_sentiment(
        self, symbol: str, headlines: list[str], social_texts: list[str], session_id: str | None = None
    ) -> dict[str, Any] | None:
        """Query the LLM for structured financial sentiment evaluation."""
        prompt = (
            f"You are a professional financial hedge fund analyst. Analyze the sentiment of the following news headlines "
            f"and Reddit social posts for the stock symbol: {symbol}.\n\n"
            f"News headlines:\n" + "\n".join(f"- {h}" for h in headlines[:8]) + "\n\n"
            "Social media posts:\n" + "\n".join(f"- {s}" for s in social_texts[:8]) + "\n\n"
            "Generate a JSON object conforming exactly to this structure:\n"
            "{\n"
            '  "score": <integer between -100 (highly bearish) and 100 (highly bullish)>,\n'
            '  "rating": <"BUY", "HOLD", or "SELL">,\n'
            '  "summary": <brief 2-3 sentence executive synthesis summary of the narrative sentiment>,\n'
            '  "opportunities": [<string list of 2-3 key opportunities or positive catalysts mentioned>],\n'
            '  "threats": [<string list of 2-3 key risks or threats mentioned>]\n'
            "}\n"
            "Ensure the response is valid JSON only."
        )

        result = await llm_client.complete(
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional financial analytics tool returning strictly structured JSON output.",
                },
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
            session_id=session_id,
            timeout=12.0,
        )

        if not result:
            return None

        try:
            content = json.loads(result.content)
            return {
                "symbol": symbol,
                "score": int(content.get("score", 0)),
                "rating": str(content.get("rating", "HOLD")).upper(),
                "summary": str(content.get("summary", "Neutral market expectations.")),
                "opportunities": list(content.get("opportunities", [])),
                "threats": list(content.get("threats", [])),
                "source": f"llm:{result.model_used}",
            }
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(f"Failed to parse LLM sentiment response: {e}")
            return None

    def _evaluate_local_sentiment(
        self, symbol: str, headlines: list[str], social_texts: list[str], combined_text: str
    ) -> dict[str, Any]:
        """Perform heuristic lexical analysis on aggregated text, yielding structured fallbacks."""
        text = combined_text.lower()

        pos_words = [
            "bullish",
            "beat",
            "upgrade",
            "buy",
            "growth",
            "momentum",
            "positive",
            "strong",
            "gain",
            "exceed",
            "outperform",
            "profit",
            "record",
            "support",
            "demand",
            "catalyst",
            "optimistic",
            "win",
            "success",
            "robust",
            "high",
            "accumulate",
        ]

        neg_words = [
            "bearish",
            "miss",
            "downgrade",
            "sell",
            "decline",
            "drop",
            "loss",
            "cut",
            "negative",
            "weak",
            "short",
            "threat",
            "risk",
            "headwind",
            "drawdown",
            "compress",
            "caution",
            "headwinds",
            "war",
            "pressure",
            "dilution",
            "sluggish",
            "expensive",
            "concern",
        ]

        pos_count = sum(text.count(word) for word in pos_words)
        neg_count = sum(text.count(word) for word in neg_words)

        total = pos_count + neg_count
        if total > 0:
            raw_score = (pos_count - neg_count) / total
            # Scale to -100 to +100
            score = int(raw_score * 100)
        else:
            score = 0

        score = max(-100, min(100, score))

        if score >= 20:
            rating = "BUY"
        elif score <= -20:
            rating = "SELL"
        else:
            rating = "HOLD"

        summary = f"Aggregated news and social mentions show a {rating.lower()}-leaning outlook for {symbol}, based on {total} sentiment-bearing terms across {len(headlines)} headlines and {len(social_texts)} social posts."
        opportunities = [
            f"Consistent baseline operational stability for {symbol}",
            "Inbound sector capital flows supporting market caps",
        ]
        threats = [
            "Macro interest rate fluctuations affecting growth stock multiples",
            "Potential short-term volatility around upcoming earnings reports",
        ]

        return {
            "symbol": symbol,
            "score": score,
            "rating": rating,
            "summary": summary,
            "opportunities": opportunities,
            "threats": threats,
            "source": "local_lexical_fallback",
        }


sentiment_service = SentimentService()
