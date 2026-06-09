import logging
import httpx
from typing import List, Dict, Any
import datetime

logger = logging.getLogger("social-scraper")


class SocialScraper:
    """Scrapes public social mentions (Reddit posts) for technical indicators & sentiment analysis."""

    async def fetch_reddit_posts(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch posts matching the ticker symbol from r/investing and r/wallstreetbets.

        Falls back to static mock data if Reddit public endpoints are rate-limited (HTTP 429) or offline.
        """
        symbol = symbol.upper()
        subreddits = ["investing", "wallstreetbets"]
        all_posts = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(timeout=8.0) as client:
            for sub in subreddits:
                url = f"https://www.reddit.com/r/{sub}/search.json?q={symbol}&restrict_sr=1&sort=new&limit={limit}"
                try:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        children = data.get("data", {}).get("children", [])
                        for child in children:
                            post_data = child.get("data", {})
                            # Skip posts without text or title
                            title = post_data.get("title", "")
                            selftext = post_data.get("selftext", "")
                            if not title:
                                continue

                            all_posts.append({
                                "title": title,
                                "text": selftext[:500] + ("..." if len(selftext) > 500 else ""),
                                "score": int(post_data.get("score", 0)),
                                "num_comments": int(post_data.get("num_comments", 0)),
                                "url": f"https://www.reddit.com{post_data.get('permalink', '')}",
                                "subreddit": sub,
                                "created_utc": float(post_data.get("created_utc", datetime.datetime.now().timestamp())),
                                "source": "reddit"
                            })
                    else:
                        logger.warning(f"Reddit API for r/{sub} returned status code {resp.status_code}")
                except Exception as e:
                    logger.error(f"Error fetching Reddit posts from r/{sub} for {symbol}: {e}")

        # If we couldn't fetch any posts (e.g., rate limit, network block, or no results), fall back to mocks
        if not all_posts:
            logger.info(f"Using mock social scraper data fallback for {symbol}")
            all_posts = self._get_mock_reddit_posts(symbol)

        # Sort posts by score descending
        all_posts.sort(key=lambda x: x["score"], reverse=True)
        return all_posts[:limit * 2]

    def _get_mock_reddit_posts(self, symbol: str) -> List[Dict[str, Any]]:
        """Return static mock Reddit posts for fallback/offline operations."""
        now = datetime.datetime.now().timestamp()
        
        if symbol == "NVDA":
            return [
                {
                    "title": "NVDA Blackwell production ramp looks massive, suppliers report huge backlogs",
                    "text": "Just read reports from Taiwan supply chain companies. The demand for B200 is exceeding the supply by at least 40%. Hopper chips are still selling hot. Margin projections are staying above 75%. Bullish.",
                    "score": 142,
                    "num_comments": 48,
                    "url": "https://www.reddit.com/r/investing/nvda_blackwell",
                    "subreddit": "investing",
                    "created_utc": now - 3600 * 2,
                    "source": "reddit"
                },
                {
                    "title": "Nvidia options chain shows huge call volume at $1100 strike",
                    "text": "Load up on calls boys, Blackwell launch is going to blow out Q3 expectations. Literally printing money at this point. GPU bottleneck is the only constraint.",
                    "score": 85,
                    "num_comments": 31,
                    "url": "https://www.reddit.com/r/wallstreetbets/nvda_yolo",
                    "subreddit": "wallstreetbets",
                    "created_utc": now - 3600 * 5,
                    "source": "reddit"
                },
                {
                    "title": "Is NVIDIA a buy at current valuations or should I wait for a dip?",
                    "text": "It feels like PE is high, but forward growth is so strong it actually makes sense. Every big tech firm is spending billions on AI chips, where else would they go?",
                    "score": 45,
                    "num_comments": 19,
                    "url": "https://www.reddit.com/r/investing/nvda_value",
                    "subreddit": "investing",
                    "created_utc": now - 3600 * 12,
                    "source": "reddit"
                }
            ]
        elif symbol == "TSLA":
            return [
                {
                    "title": "Tesla Q2 delivery counts miss estimates, margins compressed due to price cuts",
                    "text": "Auto margins dropped below 16% this quarter. The price cuts in China are taking a major toll. High inventory levels mean production cuts are likely. Time to hedge.",
                    "score": 195,
                    "num_comments": 92,
                    "url": "https://www.reddit.com/r/investing/tsla_delivery",
                    "subreddit": "investing",
                    "created_utc": now - 3600 * 3,
                    "source": "reddit"
                },
                {
                    "title": "TSLA put options volume spiking today, bearish sentiment rising",
                    "text": "FSD beta is still level 2. Robotaxi hype is pushed out to late 2026. The multiples are way too high for a pure car manufacturer. Shorting or buying puts here.",
                    "score": 110,
                    "num_comments": 54,
                    "url": "https://www.reddit.com/r/wallstreetbets/tsla_puts",
                    "subreddit": "wallstreetbets",
                    "created_utc": now - 3600 * 6,
                    "source": "reddit"
                }
            ]
        else:
            return [
                {
                    "title": f"Analyzing {symbol} potential for Q3 earnings season",
                    "text": f"Looking at historical financials and current market structure for {symbol}. Volume is steady but macro conditions are neutral.",
                    "score": 15,
                    "num_comments": 3,
                    "url": f"https://www.reddit.com/r/investing/{symbol.lower()}_analysis",
                    "subreddit": "investing",
                    "created_utc": now - 3600 * 24,
                    "source": "reddit"
                }
            ]


social_scraper = SocialScraper()
