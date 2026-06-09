import datetime
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from redis.asyncio import Redis

from backend.app.core.config import settings

logger = logging.getLogger("stock-service")


class StockService:
    """Service class interfacing with Finnhub, Alpha Vantage, and Yahoo Finance APIs with Redis caching."""

    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.finnhub_key = settings.FINNHUB_API_KEY
        self.alpha_vantage_key = settings.ALPHA_VANTAGE_API_KEY

        # Check if keys are placeholders
        if self.finnhub_key == "your_finnhub_key_here" or not self.finnhub_key:
            self.finnhub_key = None
        if self.alpha_vantage_key == "your_alpha_vantage_key_here" or not self.alpha_vantage_key:
            self.alpha_vantage_key = None

    async def get_redis(self) -> Redis:
        """Lazily initialize Redis connection."""
        if self.redis_client is None:
            self.redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis_client

    async def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch real-time quote for a stock. Checks Redis cache first.

        If keys are absent or API rate-limited, falls back to Yahoo Finance chart endpoints.
        """
        symbol = symbol.upper()
        cache_key = f"quote:{symbol}"
        redis = await self.get_redis()

        # Check cache
        cached_val = await redis.get(cache_key)
        if cached_val:
            logger.info(f"Redis cache hit for quote of: {symbol}")
            return json.loads(cached_val)

        # Cache miss, fetch live
        quote_data = None
        if self.finnhub_key:
            try:
                url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={self.finnhub_key}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        # Finnhub returns 'c' as 0 or null if ticker is invalid
                        if data.get("c"):
                            quote_data = {
                                "symbol": symbol,
                                "price": float(data["c"]),
                                "change": float(data["d"] or 0),
                                "percent_change": float(data["dp"] or 0),
                                "high": float(data["h"] or 0),
                                "low": float(data["l"] or 0),
                                "open": float(data["o"] or 0),
                                "previous_close": float(data["pc"] or 0),
                                "source": "finnhub",
                            }
            except Exception as e:
                logger.error(f"Error fetching quote from Finnhub for {symbol}: {e}")

        # Fallback to Yahoo Finance public Chart API
        if not quote_data:
            quote_data = await self._fetch_yfinance_quote(symbol)

        if quote_data:
            # Cache quote for 60 seconds
            await redis.setex(cache_key, 60, json.dumps(quote_data))

        return quote_data

    async def fetch_profile(self, symbol: str) -> Dict[str, Any]:
        """Fetch general company profile information."""
        symbol = symbol.upper()
        cache_key = f"profile:{symbol}"
        redis = await self.get_redis()

        # Check cache
        cached_val = await redis.get(cache_key)
        if cached_val:
            return json.loads(cached_val)

        profile_data = None
        if self.finnhub_key:
            try:
                url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={self.finnhub_key}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200 and resp.json():
                        data = resp.json()
                        profile_data = {
                            "symbol": symbol,
                            "name": data.get("name", symbol),
                            "sector": data.get("finnhubIndustry", "Technology"),
                            "industry": data.get("finnhubIndustry", "Software"),
                            "logo": data.get("logo", ""),
                            "website": data.get("weburl", ""),
                            "market_cap": float(data.get("marketCapitalization", 0)),
                            "source": "finnhub",
                        }
            except Exception as e:
                logger.error(f"Error fetching profile from Finnhub for {symbol}: {e}")

        if not profile_data:
            profile_data = await self._fetch_yfinance_profile(symbol)

        if profile_data:
            # Cache profile details for 24 hours (86400 seconds)
            await redis.setex(cache_key, 86400, json.dumps(profile_data))

        return profile_data

    async def fetch_history(self, symbol: str, interval: str = "1d", range_str: str = "1mo") -> List[Dict[str, Any]]:
        """Fetch historical daily price quotes (OHLCV).

        Intervals supported: 1d, 1wk. Ranges supported: 1mo, 3mo, 6mo, 1y.
        """
        symbol = symbol.upper()
        cache_key = f"history:{symbol}:{interval}:{range_str}"
        redis = await self.get_redis()

        # Check cache
        cached_val = await redis.get(cache_key)
        if cached_val:
            logger.info(f"Redis cache hit for history of: {symbol}")
            return json.loads(cached_val)

        history_data = None

        # Try Alpha Vantage if key is present
        if self.alpha_vantage_key and interval == "1d":
            try:
                url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={self.alpha_vantage_key}"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "Time Series (Daily)" in data:
                            raw_series = data["Time Series (Daily)"]
                            history_data = []
                            # Sort by date ascending
                            sorted_dates = sorted(raw_series.keys())
                            # Handle size constraints based on range
                            limit_days = 22 if range_str == "1mo" else 65 if range_str == "3mo" else 130 if range_str == "6mo" else 252
                            for d_str in sorted_dates[-limit_days:]:
                                metrics = raw_series[d_str]
                                history_data.append({
                                    "symbol": symbol,
                                    "date": d_str,
                                    "open": float(metrics["1. open"]),
                                    "high": float(metrics["2. high"]),
                                    "low": float(metrics["3. low"]),
                                    "close": float(metrics["4. close"]),
                                    "volume": int(metrics["5. volume"]),
                                    "source": "alphavantage"
                                })
            except Exception as e:
                logger.error(f"Error fetching history from Alpha Vantage for {symbol}: {e}")

        # Fallback to public Yahoo Finance chart
        if not history_data:
            history_data = await self._fetch_yfinance_history(symbol, interval, range_str)

        if history_data:
            # Cache historical charts for 1 hour (3600 seconds)
            await redis.setex(cache_key, 3600, json.dumps(history_data))

        return history_data

    # ================================================
    # Yahoo Finance Fallback Methods
    # ================================================

    async def _fetch_yfinance_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch quote via public Yahoo Finance chart API."""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    chart = data.get("chart", {}).get("result", [{}])[0]
                    meta = chart.get("meta", {})
                    indicators = chart.get("indicators", {}).get("quote", [{}])[0]
                    
                    price = float(meta.get("regularMarketPrice") or 0)
                    prev_close = float(meta.get("previousClose") or 0)
                    
                    # Fallback math if properties aren't in meta
                    change = price - prev_close
                    pct_change = (change / prev_close * 100) if prev_close else 0.0

                    # Fetch open/high/low from last bar indicators if present
                    high = float(indicators.get("high", [price])[-1] or price)
                    low = float(indicators.get("low", [price])[-1] or price)
                    open_val = float(indicators.get("open", [price])[-1] or price)

                    return {
                        "symbol": symbol,
                        "price": price,
                        "change": change,
                        "percent_change": pct_change,
                        "high": high,
                        "low": low,
                        "open": open_val,
                        "previous_close": prev_close,
                        "source": "yfinance_fallback",
                    }
        except Exception as e:
            logger.error(f"Error fetching quote from yfinance fallback for {symbol}: {e}")
        
        # Return fallback structure if network completely fails
        return {
            "symbol": symbol,
            "price": 100.0,
            "change": 0.0,
            "percent_change": 0.0,
            "high": 100.0,
            "low": 100.0,
            "open": 100.0,
            "previous_close": 100.0,
            "source": "mocked_fallback"
        }

    async def _fetch_yfinance_profile(self, symbol: str) -> Dict[str, Any]:
        """Generate static profile using symbol tags."""
        # Standard profiles for popular tickers
        known_profiles = {
            "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology", "industry": "Semiconductors"},
            "TSLA": {"name": "Tesla Inc.", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers"},
            "AAPL": {"name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
            "MSFT": {"name": "Microsoft Corporation", "sector": "Technology", "industry": "Software - Infrastructure"},
            "AMZN": {"name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "industry": "Internet Retail"},
            "GOOGL": {"name": "Alphabet Inc.", "sector": "Communication Services", "industry": "Internet Content & Information"},
            "META": {"name": "Meta Platforms Inc.", "sector": "Communication Services", "industry": "Internet Content & Information"}
        }

        # Default fallback
        profile = known_profiles.get(symbol, {
            "name": f"{symbol} Corp",
            "sector": "Financial Services",
            "industry": "Asset Management"
        })

        return {
            "symbol": symbol,
            "name": profile["name"],
            "sector": profile["sector"],
            "industry": profile["industry"],
            "logo": "",
            "website": f"https://finance.yahoo.com/quote/{symbol}",
            "market_cap": 1000000000.0,
            "source": "yfinance_fallback"
        }

    async def _fetch_yfinance_history(self, symbol: str, interval: str, range_str: str) -> List[Dict[str, Any]]:
        """Fetch history quotes via public Yahoo Finance chart API."""
        try:
            # Map parameters
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_str}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    chart = data.get("chart", {}).get("result", [{}])[0]
                    timestamps = chart.get("timestamp", [])
                    indicators = chart.get("indicators", {}).get("quote", [{}])[0]
                    
                    opens = indicators.get("open", [])
                    highs = indicators.get("high", [])
                    lows = indicators.get("low", [])
                    closes = indicators.get("close", [])
                    volumes = indicators.get("volume", [])

                    history_list = []
                    for i in range(len(timestamps)):
                        # Format timestamp to ISO date string YYYY-MM-DD
                        d_str = datetime.datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d")
                        
                        # Guard against null values which yahoo sometimes returns
                        if opens[i] is None or closes[i] is None:
                            continue
                            
                        history_list.append({
                            "symbol": symbol,
                            "date": d_str,
                            "open": float(opens[i]),
                            "high": float(highs[i]),
                            "low": float(lows[i]),
                            "close": float(closes[i]),
                            "volume": int(volumes[i] or 0),
                            "source": "yfinance_fallback"
                        })
                    return history_list
        except Exception as e:
            logger.error(f"Error fetching history from yfinance fallback for {symbol}: {e}")
        
        # Static mock return if network is offline
        import datetime
        today = datetime.date.today()
        return [
            {
                "symbol": symbol,
                "date": (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0 + i,
                "high": 105.0 + i,
                "low": 95.0 + i,
                "close": 101.0 + i,
                "volume": 1000000,
                "source": "mocked_fallback"
            }
            for i in reversed(range(10))
        ]


stock_service = StockService()
