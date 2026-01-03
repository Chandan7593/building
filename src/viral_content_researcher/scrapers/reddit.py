"""
Reddit scraper for marketing-related subreddits
"""

from datetime import datetime, timezone
from typing import Optional
import re

from viral_content_researcher.scrapers.base import BaseScraper
from viral_content_researcher.models import Topic, TrendSource, ContentCategory


# Marketing-related subreddits to monitor
MARKETING_SUBREDDITS = [
    "marketing",
    "digital_marketing",
    "socialmedia",
    "SEO",
    "content_marketing",
    "PPC",
    "advertising",
    "Entrepreneur",
    "startups",
    "growthacking",
    "ecommerce",
    "shopify",
    "copywriting",
    "emailmarketing",
    "analytics",
    "bigseo",
    "juststart",
    "affiliatemarketing",
    "dropship",
    "SaaS",
]


class RedditScraper(BaseScraper):
    """Scraper for Reddit marketing subreddits"""

    source = TrendSource.REDDIT
    base_url = "https://www.reddit.com"

    def __init__(self, subreddits: Optional[list[str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.subreddits = subreddits or MARKETING_SUBREDDITS

    def _get_headers(self) -> dict:
        return {
            "User-Agent": "ViralContentResearcher/1.0 (Marketing Research Bot)",
            "Accept": "application/json",
        }

    def _categorize_subreddit(self, subreddit: str) -> ContentCategory:
        """Map subreddit to content category"""
        mapping = {
            "seo": ContentCategory.SEO,
            "bigseo": ContentCategory.SEO,
            "socialmedia": ContentCategory.SOCIAL_MEDIA,
            "emailmarketing": ContentCategory.EMAIL_MARKETING,
            "content_marketing": ContentCategory.CONTENT_MARKETING,
            "copywriting": ContentCategory.CONTENT_MARKETING,
            "ppc": ContentCategory.PAID_ADS,
            "advertising": ContentCategory.PAID_ADS,
            "analytics": ContentCategory.ANALYTICS,
            "growthacking": ContentCategory.GROWTH_HACKING,
            "entrepreneur": ContentCategory.STARTUP,
            "startups": ContentCategory.STARTUP,
            "saas": ContentCategory.B2B,
            "ecommerce": ContentCategory.ECOMMERCE,
            "shopify": ContentCategory.ECOMMERCE,
            "dropship": ContentCategory.ECOMMERCE,
        }
        return mapping.get(subreddit.lower(), ContentCategory.GENERAL)

    def _extract_keywords(self, title: str, selftext: str = "") -> list[str]:
        """Extract potential keywords from content"""
        text = f"{title} {selftext}".lower()

        # Common marketing keywords to look for
        marketing_keywords = [
            "seo", "ppc", "roi", "ctr", "conversion", "funnel", "leads",
            "traffic", "organic", "paid", "social media", "content",
            "email", "automation", "analytics", "strategy", "campaign",
            "brand", "influencer", "viral", "engagement", "audience",
            "targeting", "retargeting", "cpc", "cpm", "impressions",
            "reach", "awareness", "acquisition", "retention", "churn",
            "saas", "b2b", "b2c", "ecommerce", "shopify", "amazon",
            "facebook", "instagram", "tiktok", "linkedin", "twitter",
            "google", "youtube", "pinterest", "reddit", "ai", "chatgpt",
            "automation", "personalization", "segmentation", "a/b test",
        ]

        found_keywords = []
        for kw in marketing_keywords:
            if kw in text:
                found_keywords.append(kw)

        return found_keywords[:10]  # Limit to top 10

    async def fetch_trending(self, limit: int = 25) -> list[Topic]:
        """Fetch hot posts from marketing subreddits"""
        topics = []

        for subreddit in self.subreddits:
            try:
                url = f"{self.base_url}/r/{subreddit}/hot.json"
                params = {"limit": min(limit, 25)}

                data = await self._fetch(url, params)

                for post in data.get("data", {}).get("children", []):
                    post_data = post.get("data", {})

                    # Skip stickied/pinned posts
                    if post_data.get("stickied"):
                        continue

                    # Skip very low engagement posts
                    if post_data.get("score", 0) < 10:
                        continue

                    topic = Topic(
                        id=post_data.get("id"),
                        title=post_data.get("title", ""),
                        description=post_data.get("selftext", "")[:500] if post_data.get("selftext") else None,
                        url=f"https://reddit.com{post_data.get('permalink', '')}",
                        source=TrendSource.REDDIT,
                        category=self._categorize_subreddit(subreddit),
                        score=post_data.get("score", 0),
                        comments=post_data.get("num_comments", 0),
                        author=post_data.get("author"),
                        published_at=datetime.fromtimestamp(
                            post_data.get("created_utc", 0),
                            tz=timezone.utc
                        ),
                        keywords=self._extract_keywords(
                            post_data.get("title", ""),
                            post_data.get("selftext", "")
                        ),
                    )

                    topic.virality_score = self.calculate_virality_score(topic)
                    topics.append(topic)

            except Exception as e:
                # Log error but continue with other subreddits
                print(f"Error fetching r/{subreddit}: {e}")
                continue

        # Sort by virality score
        topics.sort(key=lambda x: x.virality_score, reverse=True)
        return topics[:limit]

    async def search(self, query: str, limit: int = 25) -> list[Topic]:
        """Search Reddit for marketing topics"""
        topics = []

        try:
            url = f"{self.base_url}/search.json"
            params = {
                "q": f"{query} subreddit:marketing OR subreddit:digital_marketing OR subreddit:SEO OR subreddit:socialmedia",
                "sort": "relevance",
                "t": "week",
                "limit": limit,
            }

            data = await self._fetch(url, params)

            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})

                topic = Topic(
                    id=post_data.get("id"),
                    title=post_data.get("title", ""),
                    description=post_data.get("selftext", "")[:500] if post_data.get("selftext") else None,
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    source=TrendSource.REDDIT,
                    category=self._categorize_subreddit(post_data.get("subreddit", "")),
                    score=post_data.get("score", 0),
                    comments=post_data.get("num_comments", 0),
                    author=post_data.get("author"),
                    published_at=datetime.fromtimestamp(
                        post_data.get("created_utc", 0),
                        tz=timezone.utc
                    ),
                    keywords=self._extract_keywords(
                        post_data.get("title", ""),
                        post_data.get("selftext", "")
                    ),
                )

                topic.virality_score = self.calculate_virality_score(topic)
                topics.append(topic)

        except Exception as e:
            print(f"Error searching Reddit: {e}")

        return topics

    async def fetch_subreddit(self, subreddit: str, sort: str = "hot", limit: int = 25) -> list[Topic]:
        """Fetch posts from a specific subreddit"""
        topics = []

        try:
            url = f"{self.base_url}/r/{subreddit}/{sort}.json"
            params = {"limit": limit}

            data = await self._fetch(url, params)

            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})

                if post_data.get("stickied"):
                    continue

                topic = Topic(
                    id=post_data.get("id"),
                    title=post_data.get("title", ""),
                    description=post_data.get("selftext", "")[:500] if post_data.get("selftext") else None,
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    source=TrendSource.REDDIT,
                    category=self._categorize_subreddit(subreddit),
                    score=post_data.get("score", 0),
                    comments=post_data.get("num_comments", 0),
                    author=post_data.get("author"),
                    published_at=datetime.fromtimestamp(
                        post_data.get("created_utc", 0),
                        tz=timezone.utc
                    ),
                    keywords=self._extract_keywords(
                        post_data.get("title", ""),
                        post_data.get("selftext", "")
                    ),
                )

                topic.virality_score = self.calculate_virality_score(topic)
                topics.append(topic)

        except Exception as e:
            print(f"Error fetching r/{subreddit}: {e}")

        return topics
