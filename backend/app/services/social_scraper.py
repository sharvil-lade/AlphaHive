import logging
from typing import List, Dict, Any

logger = logging.getLogger("social-scraper")


class SocialScraper:
    """Deprecated: anonymous Reddit JSON scraping is blocked (confirmed 403) as of mid-2026.

    Kept as a no-op shim so `sentiment_service` doesn't need a call-site change.
    Sentiment is derived from news headlines only until a real OAuth-based
    Reddit integration is built (see plan's deferred items).
    """

    async def fetch_reddit_posts(self, symbol: str) -> List[Dict[str, Any]]:
        logger.debug(f"Skipping social scrape for {symbol} — anonymous Reddit access is unavailable.")
        return []


social_scraper = SocialScraper()
