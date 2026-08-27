import datetime
import json
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger("stock-service")

# Common NSE-listed large/mid-cap tickers that users are likely to type without
# a ".NS"/".BO" suffix (e.g. "Reliance" -> "RELIANCE"). Not exhaustive — the
# router node (chat query understanding) is the primary source of market hints;
# this is a lightweight heuristic for direct API/ticker-only callers.
INDIAN_TICKER_HINTS = {
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "HINDUNILVR",
    "ITC",
    "BHARTIARTL",
    "KOTAKBANK",
    "LT",
    "AXISBANK",
    "ASIANPAINT",
    "MARUTI",
    "SUNPHARMA",
    "TITAN",
    "WIPRO",
    "ULTRACEMCO",
    "NESTLEIND",
    "BAJFINANCE",
    "HCLTECH",
    "ADANIENT",
    "TATAMOTORS",
    "TATASTEEL",
    "ONGC",
    "NTPC",
    "POWERGRID",
}

# Static last-resort profile enrichment, keyed by the exact symbol form each
# entry is looked up with (Indian entries are keyed by their .NS-suffixed form).
KNOWN_PROFILES = {
    "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology", "industry": "Semiconductors"},
    "TSLA": {"name": "Tesla Inc.", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers"},
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
    "MSFT": {
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "industry": "Software - Infrastructure",
    },
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "industry": "Internet Retail"},
    "GOOGL": {
        "name": "Alphabet Inc.",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
    },
    "META": {
        "name": "Meta Platforms Inc.",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
    },
    "RELIANCE.NS": {
        "name": "Reliance Industries Limited",
        "sector": "Energy",
        "industry": "Oil & Gas Refining & Marketing",
    },
    "TCS.NS": {"name": "Tata Consultancy Services", "sector": "Technology", "industry": "IT Services"},
    "INFY.NS": {"name": "Infosys Limited", "sector": "Technology", "industry": "IT Services"},
}


class StockService:
    """Service class interfacing with Finnhub, Twelve Data, Alpha Vantage, Yahoo Finance,
    and BSE India, with India-primary market resolution and Redis caching."""

    def __init__(self):
        self.finnhub_key = settings.FINNHUB_API_KEY
        self.alpha_vantage_key = settings.ALPHA_VANTAGE_API_KEY
        self.twelve_data_key = settings.TWELVE_DATA_API_KEY

        if self.finnhub_key == "your_finnhub_key_here" or not self.finnhub_key:
            self.finnhub_key = None
        if self.alpha_vantage_key == "your_alpha_vantage_key_here" or not self.alpha_vantage_key:
            self.alpha_vantage_key = None
        if not self.twelve_data_key:
            self.twelve_data_key = None

    @staticmethod
    def resolve_market(symbol: str) -> str:
        """Return 'IN' for NSE/BSE-listed symbols, else 'US'."""
        s = symbol.upper()
        if s.endswith(".NS") or s.endswith(".BO"):
            return "IN"
        if s in INDIAN_TICKER_HINTS:
            return "IN"
        return "US"

    @staticmethod
    def indian_yahoo_candidates(symbol: str) -> list[str]:
        """Yahoo Finance chart symbols to try, in order, for an Indian ticker."""
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            return [symbol]
        return [f"{symbol}.NS", f"{symbol}.BO"]

    async def fetch_quote(self, symbol: str) -> dict[str, Any] | None:
        """Fetch real-time quote for a stock. Checks Redis cache first.

        Indian tickers: Yahoo Finance (.NS then .BO) -> BSE India public API.
        US/other tickers: Finnhub -> Twelve Data -> Yahoo Finance.
        Returns None if every source fails (never fabricates a placeholder price).
        """
        symbol = symbol.upper()
        cache_key = f"quote:{symbol}"
        redis = get_redis()

        cached_val = await redis.get(cache_key)
        if cached_val:
            logger.info(f"Redis cache hit for quote of: {symbol}")
            return json.loads(cached_val)

        market = self.resolve_market(symbol)
        quote_data = None

        if market == "IN":
            quote_data = await self._fetch_indian_quote(symbol)
        else:
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

            if not quote_data:
                quote_data = await self._fetch_twelvedata_quote(symbol)

            if not quote_data:
                quote_data = await self._fetch_yfinance_quote(symbol)
                if quote_data:
                    quote_data["symbol"] = symbol

        if quote_data:
            await redis.setex(cache_key, 60, json.dumps(quote_data))

        return quote_data

    async def _fetch_indian_quote(self, symbol: str) -> dict[str, Any] | None:
        """Indian-market quote chain: Yahoo Finance (.NS then .BO) -> BSE India."""
        for candidate in self.indian_yahoo_candidates(symbol):
            data = await self._fetch_yfinance_quote(candidate)
            if data:
                data["symbol"] = symbol
                return data

        base = symbol.split(".")[0]
        return await self._fetch_bse_quote(base)

    async def fetch_profile(self, symbol: str) -> dict[str, Any] | None:
        """Fetch general company profile information."""
        symbol = symbol.upper()
        cache_key = f"profile:{symbol}"
        redis = get_redis()

        cached_val = await redis.get(cache_key)
        if cached_val:
            return json.loads(cached_val)

        market = self.resolve_market(symbol)
        profile_data = None

        if market != "IN" and self.finnhub_key:
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

        if not profile_data and market != "IN":
            profile_data = await self._fetch_twelvedata_profile(symbol)

        if not profile_data:
            # For Indian tickers, try the .NS/.BO-suffixed form first so the static
            # known_profiles lookup below can actually match (it's keyed by the
            # suffixed symbol, e.g. "RELIANCE.NS"), then normalize back to the
            # original bare symbol the caller asked about.
            lookup_symbol = symbol
            if market == "IN":
                for candidate in self.indian_yahoo_candidates(symbol):
                    if candidate in KNOWN_PROFILES:
                        lookup_symbol = candidate
                        break
            profile_data = await self._fetch_yfinance_profile(lookup_symbol)
            if profile_data:
                profile_data["symbol"] = symbol

        if profile_data:
            await redis.setex(cache_key, 86400, json.dumps(profile_data))

        return profile_data

    async def fetch_history(
        self, symbol: str, interval: str = "1d", range_str: str = "1mo"
    ) -> list[dict[str, Any]]:
        """Fetch historical daily price quotes (OHLCV).

        Intervals supported: 1d, 1wk. Ranges supported: 1mo, 3mo, 6mo, 1y.
        Indian tickers: Yahoo Finance (.NS then .BO). US/other: Alpha Vantage -> Twelve Data -> Yahoo Finance.
        Returns an empty list if every source fails.
        """
        symbol = symbol.upper()
        cache_key = f"history:{symbol}:{interval}:{range_str}"
        redis = get_redis()

        cached_val = await redis.get(cache_key)
        if cached_val:
            logger.info(f"Redis cache hit for history of: {symbol}")
            return json.loads(cached_val)

        market = self.resolve_market(symbol)
        history_data = None

        if market == "IN":
            history_data = await self._fetch_indian_history(symbol, interval, range_str)
        else:
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
                                sorted_dates = sorted(raw_series.keys())
                                limit_days = (
                                    22
                                    if range_str == "1mo"
                                    else 65
                                    if range_str == "3mo"
                                    else 130
                                    if range_str == "6mo"
                                    else 252
                                )
                                for d_str in sorted_dates[-limit_days:]:
                                    metrics = raw_series[d_str]
                                    history_data.append(
                                        {
                                            "symbol": symbol,
                                            "date": d_str,
                                            "open": float(metrics["1. open"]),
                                            "high": float(metrics["2. high"]),
                                            "low": float(metrics["3. low"]),
                                            "close": float(metrics["4. close"]),
                                            "volume": int(metrics["5. volume"]),
                                            "source": "alphavantage",
                                        }
                                    )
                except Exception as e:
                    logger.error(f"Error fetching history from Alpha Vantage for {symbol}: {e}")

            if not history_data:
                history_data = await self._fetch_twelvedata_history(symbol, interval, range_str)

            if not history_data:
                history_data = await self._fetch_yfinance_history(symbol, interval, range_str)

        if history_data:
            await redis.setex(cache_key, 3600, json.dumps(history_data))

        return history_data or []

    async def _fetch_indian_history(self, symbol: str, interval: str, range_str: str) -> list[dict[str, Any]]:
        """Indian-market history chain: Yahoo Finance (.NS then .BO)."""
        for candidate in self.indian_yahoo_candidates(symbol):
            data = await self._fetch_yfinance_history(candidate, interval, range_str)
            if data:
                for row in data:
                    row["symbol"] = symbol
                return data
        return []

    # ── Twelve Data (US / other markets) ──

    async def _fetch_twelvedata_quote(self, symbol: str) -> dict[str, Any] | None:
        """Fetch quote via Twelve Data (free tier ~800 req/day with a registered key)."""
        if not self.twelve_data_key:
            return None
        try:
            url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={self.twelve_data_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("close"):
                        price = float(data["close"])
                        prev_close = float(data.get("previous_close") or price)
                        change = float(data.get("change") or (price - prev_close))
                        pct_change = float(data.get("percent_change") or 0.0)
                        return {
                            "symbol": symbol,
                            "price": price,
                            "change": change,
                            "percent_change": pct_change,
                            "high": float(data.get("high") or price),
                            "low": float(data.get("low") or price),
                            "open": float(data.get("open") or price),
                            "previous_close": prev_close,
                            "source": "twelvedata",
                        }
        except Exception as e:
            logger.error(f"Error fetching quote from Twelve Data for {symbol}: {e}")
        return None

    async def _fetch_twelvedata_profile(self, symbol: str) -> dict[str, Any] | None:
        """Fetch fundamentals via Twelve Data's /statistics endpoint."""
        if not self.twelve_data_key:
            return None
        try:
            url = f"https://api.twelvedata.com/statistics?symbol={symbol}&apikey={self.twelve_data_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    stats = data.get("statistics", {}) if isinstance(data, dict) else {}
                    valuations = stats.get("valuations_metrics", {}) if isinstance(stats, dict) else {}
                    if stats:
                        return {
                            "symbol": symbol,
                            "name": data.get("name", symbol),
                            "sector": data.get("sector", "Unknown"),
                            "industry": data.get("industry", "Unknown"),
                            "logo": "",
                            "website": "",
                            "market_cap": float(valuations.get("market_capitalization", 0) or 0),
                            "source": "twelvedata",
                        }
        except Exception as e:
            logger.error(f"Error fetching profile from Twelve Data for {symbol}: {e}")
        return None

    async def _fetch_twelvedata_history(
        self, symbol: str, interval: str, range_str: str
    ) -> list[dict[str, Any]]:
        """Fetch historical OHLCV via Twelve Data's /time_series endpoint."""
        if not self.twelve_data_key:
            return []
        try:
            output_size = {"1mo": 22, "3mo": 65, "6mo": 130, "1y": 252}.get(range_str, 22)
            td_interval = "1week" if interval == "1wk" else "1day"
            url = (
                f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={td_interval}"
                f"&outputsize={output_size}&apikey={self.twelve_data_key}"
            )
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    values = data.get("values", [])
                    history_data = []
                    for row in reversed(values):  # Twelve Data returns newest-first
                        history_data.append(
                            {
                                "symbol": symbol,
                                "date": row["datetime"][:10],
                                "open": float(row["open"]),
                                "high": float(row["high"]),
                                "low": float(row["low"]),
                                "close": float(row["close"]),
                                "volume": int(row.get("volume") or 0),
                                "source": "twelvedata",
                            }
                        )
                    return history_data
        except Exception as e:
            logger.error(f"Error fetching history from Twelve Data for {symbol}: {e}")
        return []

    # ── BSE India (Indian-market fallback) ──

    async def _fetch_bse_quote(self, scrip_code: str) -> dict[str, Any] | None:
        """Best-effort BSE India public API fallback.

        BSE's endpoint keys off a numeric scrip code, not a ticker symbol, so this
        only helps when the caller already has one (or the base ticker happens to
        be numeric). NSE-suffixed tickers are handled by the Yahoo Finance path,
        which covers the large majority of Indian equities.
        """
        if not scrip_code.isdigit():
            return None
        try:
            url = f"https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w?scripcode={scrip_code}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Origin": "https://www.bseindia.com",
                "Referer": "https://www.bseindia.com/",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    header = data.get("Header", data) if isinstance(data, dict) else {}
                    price = float(header.get("LTP") or 0)
                    if price:
                        prev_close = float(header.get("PrevClose") or price)
                        change = price - prev_close
                        return {
                            "symbol": scrip_code,
                            "price": price,
                            "change": change,
                            "percent_change": (change / prev_close * 100) if prev_close else 0.0,
                            "high": float(header.get("High") or price),
                            "low": float(header.get("Low") or price),
                            "open": float(header.get("Open") or price),
                            "previous_close": prev_close,
                            "source": "bse_india",
                        }
        except Exception as e:
            logger.error(f"Error fetching quote from BSE India for scrip {scrip_code}: {e}")
        return None

    # ── Yahoo Finance ──

    async def _fetch_yfinance_quote(self, symbol: str) -> dict[str, Any] | None:
        """Fetch quote via public Yahoo Finance chart API. Returns None on failure
        (no fabricated placeholder price) so callers can surface "data unavailable"."""
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
                    if not price:
                        return None
                    prev_close = float(meta.get("previousClose") or meta.get("chartPreviousClose") or 0)

                    change = price - prev_close
                    pct_change = (change / prev_close * 100) if prev_close else 0.0

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
                        "source": "yfinance",
                    }
        except Exception as e:
            logger.error(f"Error fetching quote from yfinance for {symbol}: {e}")

        return None

    async def _fetch_yfinance_profile(self, symbol: str) -> dict[str, Any]:
        """Generate static profile using symbol tags (last-resort profile enrichment)."""
        profile = KNOWN_PROFILES.get(
            symbol, {"name": f"{symbol} Corp", "sector": "Financial Services", "industry": "Asset Management"}
        )

        return {
            "symbol": symbol,
            "name": profile["name"],
            "sector": profile["sector"],
            "industry": profile["industry"],
            "logo": "",
            "website": f"https://finance.yahoo.com/quote/{symbol}",
            "market_cap": 1000000000.0,
            "source": "static_profile_fallback",
        }

    async def _fetch_yfinance_history(
        self, symbol: str, interval: str, range_str: str
    ) -> list[dict[str, Any]]:
        """Fetch history quotes via public Yahoo Finance chart API. Returns an empty
        list on failure (no fabricated placeholder candles)."""
        try:
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
                        d_str = datetime.datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d")

                        if opens[i] is None or closes[i] is None:
                            continue

                        history_list.append(
                            {
                                "symbol": symbol,
                                "date": d_str,
                                "open": float(opens[i]),
                                "high": float(highs[i]),
                                "low": float(lows[i]),
                                "close": float(closes[i]),
                                "volume": int(volumes[i] or 0),
                                "source": "yfinance",
                            }
                        )
                    return history_list
        except Exception as e:
            logger.error(f"Error fetching history from yfinance for {symbol}: {e}")

        return []


stock_service = StockService()
