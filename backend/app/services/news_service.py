import json
import logging
import datetime
from typing import Dict, Any, List, Optional
import httpx
from redis.asyncio import Redis

from backend.app.core.config import settings

logger = logging.getLogger("news-service")


class NewsService:
    """Service class handling company-specific news fetching and caching."""

    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.finnhub_key = settings.FINNHUB_API_KEY
        if self.finnhub_key == "your_finnhub_key_here" or not self.finnhub_key:
            self.finnhub_key = None

    async def get_redis(self) -> Redis:
        """Lazily initialize Redis connection."""
        if self.redis_client is None:
            self.redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis_client

    async def fetch_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch news articles for a company symbol. Checks Redis cache first."""
        symbol = symbol.upper()
        cache_key = f"news:{symbol}"
        redis = await self.get_redis()

        # Check cache
        cached_val = await redis.get(cache_key)
        if cached_val:
            logger.info(f"Redis cache hit for news of: {symbol}")
            return json.loads(cached_val)

        # Cache miss, fetch live
        news_data = None
        if self.finnhub_key:
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
                            # Limit to top 15 news articles
                            for item in raw_news[:15]:
                                news_data.append({
                                    "symbol": symbol,
                                    "headline": item.get("headline", ""),
                                    "summary": item.get("summary", ""),
                                    "url": item.get("url", ""),
                                    "source": item.get("source", "Finnhub"),
                                    "published_at": datetime.datetime.fromtimestamp(
                                        item.get("datetime", int(datetime.datetime.utcnow().timestamp()))
                                    ).isoformat(),
                                })
            except Exception as e:
                logger.error(f"Error fetching news from Finnhub for {symbol}: {e}")

        # Fallback to public Yahoo Finance Search API
        if not news_data:
            news_data = await self._fetch_yfinance_news(symbol)

        if news_data:
            # Cache news articles for 1 hour (3600 seconds)
            await redis.setex(cache_key, 3600, json.dumps(news_data))

        return news_data

    async def _fetch_yfinance_news(self, symbol: str) -> List[Dict[str, Any]]:
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
                        publish_time = item.get("providerPublishTime", int(datetime.datetime.utcnow().timestamp()))
                        published_at = datetime.datetime.fromtimestamp(publish_time).isoformat()
                        news_data.append({
                            "symbol": symbol,
                            "headline": item.get("title", ""),
                            "summary": item.get("summary", item.get("title", "")),
                            "url": item.get("link", ""),
                            "source": item.get("publisher", "Yahoo Finance"),
                            "published_at": published_at,
                        })
                    return news_data
        except Exception as e:
            logger.error(f"Error fetching news from yfinance search fallback for {symbol}: {e}")
        
        # Static mock news in case network is offline
        return [
            {
                "symbol": symbol,
                "headline": f"Global markets monitor active movements on {symbol}",
                "summary": f"Analysts track sector developments as {symbol} shows volume interest during current sessions.",
                "url": "https://finance.yahoo.com",
                "source": "Mock Finance",
                "published_at": datetime.datetime.utcnow().isoformat()
            }
        ]


news_service = NewsService()
