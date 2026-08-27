import datetime
import json
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger("news-service")


class NewsService:
    """Service class handling company-specific news fetching and caching."""

    def __init__(self):
        self.finnhub_key = settings.FINNHUB_API_KEY
        if self.finnhub_key == "your_finnhub_key_here" or not self.finnhub_key:
            self.finnhub_key = None
        self.marketaux_key = settings.MARKETAUX_API_KEY or None

    async def fetch_news(self, symbol: str) -> list[dict[str, Any]]:
        """Fetch news articles for a company symbol. Checks Redis cache first."""
        symbol = symbol.upper()
        cache_key = f"news:{symbol}"
        redis = get_redis()

        cached_val = await redis.get(cache_key)
        if cached_val:
            logger.info(f"Redis cache hit for news of: {symbol}")
            return json.loads(cached_val)

        # Indian tickers: Finnhub's free tier has little/no NSE/BSE coverage, and
        # Yahoo's search-based news fallback is unreliable for Indian tickers (see below).
        from app.services.stock_service import stock_service

        market = stock_service.resolve_market(symbol)

        # Cache miss, fetch live. Marketaux is finance-specific with real Indian +
        # global coverage, so it's tried first for every market.
        news_data = None
        if self.marketaux_key:
            news_data = await self._fetch_marketaux_news(symbol, market)

        if not news_data and market != "IN" and self.finnhub_key:
            try:
                # Finnhub requires date ranges. Fetch last 7 days of news.
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                week_ago_str = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

                url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={week_ago_str}&to={today_str}&token={self.finnhub_key}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        raw_news = resp.json()
                        if isinstance(raw_news, list):
                            news_data = []
                            for item in raw_news[:15]:
                                news_data.append(
                                    {
                                        "symbol": symbol,
                                        "headline": item.get("headline", ""),
                                        "summary": item.get("summary", ""),
                                        "url": item.get("url", ""),
                                        "source": item.get("source", "Finnhub"),
                                        "published_at": datetime.datetime.fromtimestamp(
                                            item.get("datetime", int(datetime.datetime.utcnow().timestamp()))
                                        ).isoformat(),
                                    }
                                )
            except Exception as e:
                logger.error(f"Error fetching news from Finnhub for {symbol}: {e}")

        # Fallback to public Yahoo Finance Search API — confirmed unreliable for Indian
        # tickers (its "news" field returns generic trending content unrelated to the
        # query, not a real per-symbol search, regardless of how the query is phrased).
        # Returning nothing is more honest than feeding sentiment analysis wrong-company
        # headlines; no verified free Indian financial news source exists yet (see plan's
        # deferred items — this needs a real Indian news API integration in a future pass).
        if not news_data and market != "IN":
            news_data = await self._fetch_yfinance_news(symbol)

        if news_data:
            await redis.setex(cache_key, 3600, json.dumps(news_data))

        return news_data or []

    async def _fetch_marketaux_news(self, symbol: str, market: str) -> list[dict[str, Any]]:
        """Fetch news via Marketaux — a finance-specific news API with real global
        (including Indian NSE/BSE) coverage, unlike the generic Yahoo search fallback."""
        from app.services.stock_service import stock_service

        candidates = stock_service.indian_yahoo_candidates(symbol) if market == "IN" else [symbol]

        for candidate in candidates:
            try:
                url = (
                    "https://api.marketaux.com/v1/news/all"
                    f"?symbols={candidate}&filter_entities=true&language=en&limit=15"
                    f"&api_token={self.marketaux_key}"
                )
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        articles = data.get("data", [])
                        if articles:
                            return [
                                {
                                    "symbol": symbol,
                                    "headline": a.get("title", ""),
                                    "summary": a.get("description") or a.get("snippet", ""),
                                    "url": a.get("url", ""),
                                    "source": a.get("source", "Marketaux"),
                                    "published_at": a.get("published_at", ""),
                                }
                                for a in articles
                            ]
                    else:
                        logger.warning(f"Marketaux returned status {resp.status_code} for {candidate}")
            except Exception as e:
                logger.error(f"Error fetching news from Marketaux for {candidate}: {e}")

        return []

    async def _fetch_yfinance_news(self, symbol: str) -> list[dict[str, Any]]:
        """Fetch news articles using the public Yahoo Search API."""
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={symbol}&newsCount=15"
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_news = data.get("news", [])
                    news_data = []
                    for item in raw_news:
                        publish_time = item.get(
                            "providerPublishTime", int(datetime.datetime.utcnow().timestamp())
                        )
                        published_at = datetime.datetime.fromtimestamp(publish_time).isoformat()
                        news_data.append(
                            {
                                "symbol": symbol,
                                "headline": item.get("title", ""),
                                "summary": item.get("summary", item.get("title", "")),
                                "url": item.get("link", ""),
                                "source": item.get("publisher", "Yahoo Finance"),
                                "published_at": published_at,
                            }
                        )
                    return news_data
        except Exception as e:
            logger.error(f"Error fetching news from yfinance search fallback for {symbol}: {e}")

        return []


news_service = NewsService()
