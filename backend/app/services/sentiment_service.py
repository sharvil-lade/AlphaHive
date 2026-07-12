import logging
import json
from typing import List, Dict, Any, Optional
from app.services.news_service import news_service
from app.services.social_scraper import social_scraper
from app.services.llm_client import llm_client

logger = logging.getLogger("sentiment-service")


class SentimentService:
    """Service to evaluate news & social sentiment using the shared LLM client, or a local lexical fallback."""

    async def analyze_sentiment(self, symbol: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate news articles and social mentions, then evaluate the unified sentiment score and summary."""
        symbol = symbol.upper()

        # 1. Gather narrative sources: News and Reddit posts
        news_items = await news_service.fetch_news(symbol)
        reddit_posts = await social_scraper.fetch_reddit_posts(symbol)

        # 2. Extract headlines/text to feed the parser
        headlines = [item.get("headline", "") for item in news_items if item.get("headline")]
        social_texts = [f"{post.get('title', '')} - {post.get('text', '')}" for post in reddit_posts]

        # Combine text for evaluation
        combined_text = "\n".join(headlines + social_texts)

        # 3. Call the LLM if the LiteLLM proxy is configured
        if llm_client.is_configured:
            llm_sentiment = await self._fetch_llm_sentiment(symbol, headlines, social_texts, session_id)
            if llm_sentiment:
                return llm_sentiment

        # 4. Fallback to Local Rule-based Lexical Analyzer
        return self._evaluate_local_sentiment(symbol, headlines, social_texts, combined_text)

    async def _fetch_llm_sentiment(self, symbol: str, headlines: List[str], social_texts: List[str], session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Query the LLM for structured financial sentiment evaluation."""
        prompt = (
            f"You are a professional financial hedge fund analyst. Analyze the sentiment of the following news headlines "
            f"and Reddit social posts for the stock symbol: {symbol}.\n\n"
            f"News headlines:\n" + "\n".join(f"- {h}" for h in headlines[:8]) + "\n\n"
            f"Social media posts:\n" + "\n".join(f"- {s}" for s in social_texts[:8]) + "\n\n"
            f"Generate a JSON object conforming exactly to this structure:\n"
            f"{{\n"
            f"  \"score\": <integer between -100 (highly bearish) and 100 (highly bullish)>,\n"
            f"  \"rating\": <\"BUY\", \"HOLD\", or \"SELL\">,\n"
            f"  \"summary\": <brief 2-3 sentence executive synthesis summary of the narrative sentiment>,\n"
            f"  \"opportunities\": [<string list of 2-3 key opportunities or positive catalysts mentioned>],\n"
            f"  \"threats\": [<string list of 2-3 key risks or threats mentioned>]\n"
            f"}}\n"
            f"Ensure the response is valid JSON only."
        )

        result = await llm_client.complete(
            messages=[
                {"role": "system", "content": "You are a professional financial analytics tool returning strictly structured JSON output."},
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

    def _evaluate_local_sentiment(self, symbol: str, headlines: List[str], social_texts: List[str], combined_text: str) -> Dict[str, Any]:
        """Perform heuristic lexical analysis on aggregated text, yielding structured fallbacks."""
        text = combined_text.lower()

        # Simple financial lexicons
        pos_words = [
            "bullish", "beat", "upgrade", "buy", "growth", "momentum", "positive", "strong", "gain",
            "exceed", "outperform", "profit", "record", "support", "demand", "catalyst", "optimistic",
            "win", "success", "robust", "high", "accumulate"
        ]

        neg_words = [
            "bearish", "miss", "downgrade", "sell", "decline", "drop", "loss", "cut", "negative", "weak",
            "short", "threat", "risk", "headwind", "drawdown", "compress", "caution", "headwinds", "war",
            "pressure", "dilution", "sluggish", "expensive", "concern"
        ]

        pos_count = sum(text.count(word) for word in pos_words)
        neg_count = sum(text.count(word) for word in neg_words)

        # Quantitative scoring math
        total = pos_count + neg_count
        if total > 0:
            raw_score = (pos_count - neg_count) / total
            # Scale to -100 to +100
            score = int(raw_score * 100)
        else:
            score = 0

        # Bound score
        score = max(-100, min(100, score))

        # Assign ratings based on score bounds
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
