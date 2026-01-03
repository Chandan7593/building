"""
RSS Feed scraper for marketing blogs and news sources
"""

from datetime import datetime, timezone
from typing import Optional
import asyncio
import feedparser

from viral_content_researcher.scrapers.base import BaseScraper
from viral_content_researcher.models import Topic, TrendSource, ContentCategory


# Default marketing RSS feeds to monitor
DEFAULT_MARKETING_FEEDS = [
    # Marketing & Growth
    ("https://blog.hubspot.com/marketing/rss.xml", "HubSpot Marketing Blog", ContentCategory.CONTENT_MARKETING),
    ("https://feeds.feedburner.com/SearchEngineLand", "Search Engine Land", ContentCategory.SEO),
    ("https://www.searchenginejournal.com/feed/", "Search Engine Journal", ContentCategory.SEO),
    ("https://feeds.feedburner.com/naborrowman", "Moz Blog", ContentCategory.SEO),
    ("https://contentmarketinginstitute.com/feed/", "Content Marketing Institute", ContentCategory.CONTENT_MARKETING),
    ("https://neilpatel.com/blog/feed/", "Neil Patel", ContentCategory.SEO),
    ("https://www.socialmediaexaminer.com/feed/", "Social Media Examiner", ContentCategory.SOCIAL_MEDIA),
    ("https://sproutsocial.com/insights/feed/", "Sprout Social Insights", ContentCategory.SOCIAL_MEDIA),
    ("https://buffer.com/resources/feed/", "Buffer Blog", ContentCategory.SOCIAL_MEDIA),

    # Tech & Startups
    ("https://techcrunch.com/feed/", "TechCrunch", ContentCategory.STARTUP),
    ("https://feeds.feedburner.com/venturebeat/SZYF", "VentureBeat", ContentCategory.AI_MARKETING),
    ("https://www.producthunt.com/feed", "Product Hunt", ContentCategory.STARTUP),

    # Analytics & Data
    ("https://www.kaushik.net/avinash/feed/", "Occam's Razor", ContentCategory.ANALYTICS),

    # Ecommerce
    ("https://www.shopify.com/blog/feed", "Shopify Blog", ContentCategory.ECOMMERCE),
    ("https://www.bigcommerce.com/blog/feed/", "BigCommerce Blog", ContentCategory.ECOMMERCE),
]


class RSSFeedScraper(BaseScraper):
    """Scraper for RSS feeds from marketing blogs"""

    source = TrendSource.RSS_FEED
    base_url = ""

    def __init__(
        self,
        feeds: Optional[list[tuple[str, str, ContentCategory]]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.feeds = feeds or DEFAULT_MARKETING_FEEDS

    def _parse_date(self, entry: dict) -> Optional[datetime]:
        """Parse date from feed entry"""
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']

        for field in date_fields:
            if entry.get(field):
                try:
                    import time
                    return datetime.fromtimestamp(
                        time.mktime(entry[field]),
                        tz=timezone.utc
                    )
                except (ValueError, TypeError):
                    continue

        return None

    def _extract_keywords(self, title: str, summary: str = "") -> list[str]:
        """Extract keywords from content"""
        text = f"{title} {summary}".lower()

        marketing_keywords = [
            "seo", "marketing", "content", "social media", "email",
            "conversion", "traffic", "leads", "sales", "roi",
            "analytics", "strategy", "campaign", "brand", "growth",
            "ai", "automation", "personalization", "engagement",
            "advertising", "ppc", "influencer", "video", "podcast",
            "newsletter", "ecommerce", "shopify", "startup", "saas",
        ]

        found = []
        for kw in marketing_keywords:
            if kw in text:
                found.append(kw)

        return found[:10]

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags from text"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator=' ', strip=True)[:500]

    async def _fetch_feed(
        self,
        feed_url: str,
        feed_name: str,
        category: ContentCategory,
        limit: int = 10
    ) -> list[Topic]:
        """Fetch and parse a single RSS feed"""
        topics = []

        try:
            # feedparser is synchronous, so we run it in executor
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, feed_url)

            for entry in feed.entries[:limit]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = self._clean_html(entry.get('summary', entry.get('description', '')))

                topic = Topic(
                    id=entry.get('id', link),
                    title=title,
                    description=summary,
                    url=link,
                    source=TrendSource.RSS_FEED,
                    category=category,
                    author=entry.get('author', feed_name),
                    published_at=self._parse_date(entry),
                    keywords=self._extract_keywords(title, summary),
                )

                # RSS feeds don't have engagement metrics, estimate virality by recency
                if topic.published_at:
                    hours_old = (datetime.now(timezone.utc) - topic.published_at).total_seconds() / 3600
                    if hours_old < 6:
                        topic.virality_score = 70
                    elif hours_old < 24:
                        topic.virality_score = 60
                    elif hours_old < 48:
                        topic.virality_score = 50
                    elif hours_old < 72:
                        topic.virality_score = 40
                    else:
                        topic.virality_score = 30
                else:
                    topic.virality_score = 35

                topics.append(topic)

        except Exception as e:
            print(f"Error fetching feed {feed_name}: {e}")

        return topics

    async def fetch_trending(self, limit: int = 25) -> list[Topic]:
        """Fetch latest posts from all configured RSS feeds"""
        all_topics = []

        # Fetch all feeds in parallel
        tasks = [
            self._fetch_feed(url, name, category, limit=5)
            for url, name, category in self.feeds
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_topics.extend(result)

        # Sort by publication date (newest first)
        all_topics.sort(
            key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )

        return all_topics[:limit]

    async def search(self, query: str, limit: int = 25) -> list[Topic]:
        """Search through fetched feed content"""
        # First fetch all feeds
        all_topics = await self.fetch_trending(limit=100)

        # Filter by query
        query_lower = query.lower()
        matching = [
            topic for topic in all_topics
            if query_lower in topic.title.lower()
            or (topic.description and query_lower in topic.description.lower())
            or any(query_lower in kw for kw in topic.keywords)
        ]

        return matching[:limit]

    async def fetch_by_category(self, category: ContentCategory, limit: int = 25) -> list[Topic]:
        """Fetch feeds filtered by category"""
        # Filter feeds by category
        category_feeds = [
            (url, name, cat) for url, name, cat in self.feeds
            if cat == category
        ]

        if not category_feeds:
            return []

        tasks = [
            self._fetch_feed(url, name, cat, limit=10)
            for url, name, cat in category_feeds
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_topics = []
        for result in results:
            if isinstance(result, list):
                all_topics.extend(result)

        all_topics.sort(
            key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )

        return all_topics[:limit]

    def add_feed(self, url: str, name: str, category: ContentCategory):
        """Add a new feed to monitor"""
        self.feeds.append((url, name, category))

    def remove_feed(self, url: str):
        """Remove a feed from monitoring"""
        self.feeds = [(u, n, c) for u, n, c in self.feeds if u != url]

    def list_feeds(self) -> list[tuple[str, str, ContentCategory]]:
        """List all configured feeds"""
        return self.feeds.copy()
