"""
Google Trends scraper for marketing-related trending topics
"""

from datetime import datetime, timezone
from typing import Optional

from viral_content_researcher.scrapers.base import BaseScraper
from viral_content_researcher.models import Topic, TrendSource, ContentCategory


class GoogleTrendsScraper(BaseScraper):
    """Scraper for Google Trends data"""

    source = TrendSource.GOOGLE_TRENDS
    base_url = "https://trends.google.com"

    # Marketing-related search terms to track
    MARKETING_TERMS = [
        "digital marketing",
        "SEO",
        "social media marketing",
        "content marketing",
        "email marketing",
        "influencer marketing",
        "marketing automation",
        "PPC advertising",
        "brand marketing",
        "growth hacking",
        "AI marketing",
        "video marketing",
        "affiliate marketing",
        "ecommerce marketing",
    ]

    def __init__(self, geo: str = "US", **kwargs):
        super().__init__(**kwargs)
        self.geo = geo
        self._pytrends = None

    def _get_pytrends(self):
        """Lazy load pytrends"""
        if self._pytrends is None:
            try:
                from pytrends.request import TrendReq
                self._pytrends = TrendReq(hl='en-US', tz=360)
            except ImportError:
                raise ImportError("pytrends is required for Google Trends. Install with: pip install pytrends")
        return self._pytrends

    def _categorize_keyword(self, keyword: str) -> ContentCategory:
        """Categorize keyword into content category"""
        keyword_lower = keyword.lower()

        if any(term in keyword_lower for term in ["seo", "search engine", "ranking", "backlink"]):
            return ContentCategory.SEO
        elif any(term in keyword_lower for term in ["social media", "instagram", "tiktok", "facebook", "linkedin"]):
            return ContentCategory.SOCIAL_MEDIA
        elif any(term in keyword_lower for term in ["email", "newsletter"]):
            return ContentCategory.EMAIL_MARKETING
        elif any(term in keyword_lower for term in ["content", "blog", "copywriting"]):
            return ContentCategory.CONTENT_MARKETING
        elif any(term in keyword_lower for term in ["ppc", "ads", "advertising", "paid"]):
            return ContentCategory.PAID_ADS
        elif any(term in keyword_lower for term in ["analytics", "data", "metrics"]):
            return ContentCategory.ANALYTICS
        elif any(term in keyword_lower for term in ["brand", "branding"]):
            return ContentCategory.BRANDING
        elif any(term in keyword_lower for term in ["growth", "viral", "hack"]):
            return ContentCategory.GROWTH_HACKING
        elif any(term in keyword_lower for term in ["influencer", "creator"]):
            return ContentCategory.INFLUENCER
        elif any(term in keyword_lower for term in ["video", "youtube"]):
            return ContentCategory.VIDEO_MARKETING
        elif any(term in keyword_lower for term in ["ai", "chatgpt", "automation"]):
            return ContentCategory.AI_MARKETING
        elif any(term in keyword_lower for term in ["ecommerce", "shopify", "amazon"]):
            return ContentCategory.ECOMMERCE

        return ContentCategory.GENERAL

    async def fetch_trending(self, limit: int = 25) -> list[Topic]:
        """Fetch trending searches from Google Trends"""
        topics = []

        try:
            pytrends = self._get_pytrends()

            # Get daily trending searches
            trending_df = pytrends.trending_searches(pn='united_states')

            for idx, row in trending_df.head(limit).iterrows():
                query = row[0]

                # Check if it's marketing-related
                is_marketing = self._is_marketing_related(query)

                topic = Topic(
                    id=f"gt_{idx}",
                    title=query,
                    description=f"Trending search: {query}",
                    url=f"https://trends.google.com/trends/explore?q={query.replace(' ', '%20')}&geo={self.geo}",
                    source=TrendSource.GOOGLE_TRENDS,
                    category=self._categorize_keyword(query) if is_marketing else ContentCategory.GENERAL,
                    score=100 - idx,  # Higher rank = higher score
                    published_at=datetime.now(timezone.utc),
                    keywords=[query.lower()],
                )

                # Boost score for marketing-related terms
                if is_marketing:
                    topic.virality_score = min(80 + (25 - idx), 100)
                else:
                    topic.virality_score = max(50 - idx, 10)

                topics.append(topic)

        except Exception as e:
            print(f"Error fetching Google Trends: {e}")

        return topics

    async def fetch_related_topics(self, keyword: str) -> list[Topic]:
        """Fetch related trending topics for a keyword"""
        topics = []

        try:
            pytrends = self._get_pytrends()
            pytrends.build_payload([keyword], timeframe='now 7-d', geo=self.geo)

            related = pytrends.related_topics()

            if keyword in related and 'rising' in related[keyword]:
                rising_df = related[keyword]['rising']

                if rising_df is not None and not rising_df.empty:
                    for idx, row in rising_df.iterrows():
                        topic_title = row.get('topic_title', row.get('query', ''))

                        topic = Topic(
                            id=f"gt_rel_{idx}",
                            title=topic_title,
                            description=f"Rising topic related to '{keyword}'",
                            url=f"https://trends.google.com/trends/explore?q={topic_title.replace(' ', '%20')}&geo={self.geo}",
                            source=TrendSource.GOOGLE_TRENDS,
                            category=self._categorize_keyword(topic_title),
                            score=int(row.get('value', 0)) if str(row.get('value', '')).isdigit() else 50,
                            keywords=[keyword.lower(), topic_title.lower()],
                            published_at=datetime.now(timezone.utc),
                        )

                        topic.virality_score = min(float(row.get('value', 50)), 100) if str(row.get('value', '')).replace('.', '').isdigit() else 50
                        topics.append(topic)

        except Exception as e:
            print(f"Error fetching related topics for '{keyword}': {e}")

        return topics

    async def search(self, query: str, limit: int = 25) -> list[Topic]:
        """Search Google Trends for interest over time"""
        topics = []

        try:
            pytrends = self._get_pytrends()
            pytrends.build_payload([query], timeframe='now 7-d', geo=self.geo)

            # Get related queries
            related_queries = pytrends.related_queries()

            if query in related_queries:
                # Rising queries
                if 'rising' in related_queries[query] and related_queries[query]['rising'] is not None:
                    rising_df = related_queries[query]['rising']
                    for idx, row in rising_df.head(limit // 2).iterrows():
                        related_query = row.get('query', '')
                        topic = Topic(
                            id=f"gt_search_rising_{idx}",
                            title=related_query,
                            description=f"Rising search related to '{query}' - {row.get('value', 'Breakout')}% increase",
                            url=f"https://trends.google.com/trends/explore?q={related_query.replace(' ', '%20')}&geo={self.geo}",
                            source=TrendSource.GOOGLE_TRENDS,
                            category=self._categorize_keyword(related_query),
                            keywords=[query.lower(), related_query.lower()],
                            published_at=datetime.now(timezone.utc),
                        )
                        topic.virality_score = 75
                        topics.append(topic)

                # Top queries
                if 'top' in related_queries[query] and related_queries[query]['top'] is not None:
                    top_df = related_queries[query]['top']
                    for idx, row in top_df.head(limit // 2).iterrows():
                        related_query = row.get('query', '')
                        topic = Topic(
                            id=f"gt_search_top_{idx}",
                            title=related_query,
                            description=f"Top search related to '{query}'",
                            url=f"https://trends.google.com/trends/explore?q={related_query.replace(' ', '%20')}&geo={self.geo}",
                            source=TrendSource.GOOGLE_TRENDS,
                            category=self._categorize_keyword(related_query),
                            keywords=[query.lower(), related_query.lower()],
                            published_at=datetime.now(timezone.utc),
                        )
                        topic.virality_score = 60
                        topics.append(topic)

        except Exception as e:
            print(f"Error searching Google Trends for '{query}': {e}")

        return topics[:limit]

    def _is_marketing_related(self, text: str) -> bool:
        """Check if text is related to marketing"""
        marketing_indicators = [
            "marketing", "seo", "ads", "advertising", "social media",
            "brand", "campaign", "content", "digital", "email",
            "influencer", "viral", "growth", "conversion", "traffic",
            "analytics", "roi", "ppc", "cpc", "engagement", "audience",
            "funnel", "leads", "sales", "ecommerce", "shopify",
            "facebook", "instagram", "tiktok", "linkedin", "twitter",
            "youtube", "google", "ai", "automation", "saas", "startup",
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in marketing_indicators)

    async def get_marketing_trends(self, limit: int = 25) -> list[Topic]:
        """Get trends specifically for marketing-related terms"""
        all_topics = []

        for term in self.MARKETING_TERMS[:5]:  # Limit API calls
            try:
                related = await self.fetch_related_topics(term)
                all_topics.extend(related)
            except Exception:
                continue

        # Deduplicate by title
        seen_titles = set()
        unique_topics = []
        for topic in all_topics:
            if topic.title.lower() not in seen_titles:
                seen_titles.add(topic.title.lower())
                unique_topics.append(topic)

        # Sort by virality score
        unique_topics.sort(key=lambda x: x.virality_score, reverse=True)
        return unique_topics[:limit]
