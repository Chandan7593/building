"""
Main researcher class that orchestrates all scrapers and curation
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from viral_content_researcher.models import (
    Topic,
    ContentCategory,
    TrendSource,
    ResearchSession,
)
from viral_content_researcher.curator import ContentCurator
from viral_content_researcher.scrapers import (
    RedditScraper,
    GoogleTrendsScraper,
    HackerNewsScraper,
    RSSFeedScraper,
    ProductHuntScraper,
)


class ViralContentResearcher:
    """
    Main class for researching viral marketing content.
    Coordinates multiple data sources and curates results.
    """

    def __init__(
        self,
        sources: Optional[list[TrendSource]] = None,
        curator: Optional[ContentCurator] = None,
    ):
        """
        Initialize the researcher.

        Args:
            sources: List of sources to use (None = all available)
            curator: Custom curator instance (uses default if None)
        """
        self.sources = sources or [
            TrendSource.REDDIT,
            TrendSource.HACKER_NEWS,
            TrendSource.RSS_FEED,
            TrendSource.PRODUCT_HUNT,
        ]

        self.curator = curator or ContentCurator()
        self._scrapers = {}
        self._session: Optional[ResearchSession] = None

    def _get_scraper(self, source: TrendSource):
        """Get or create scraper for a source"""
        if source not in self._scrapers:
            if source == TrendSource.REDDIT:
                self._scrapers[source] = RedditScraper()
            elif source == TrendSource.GOOGLE_TRENDS:
                self._scrapers[source] = GoogleTrendsScraper()
            elif source == TrendSource.HACKER_NEWS:
                self._scrapers[source] = HackerNewsScraper()
            elif source == TrendSource.RSS_FEED:
                self._scrapers[source] = RSSFeedScraper()
            elif source == TrendSource.PRODUCT_HUNT:
                self._scrapers[source] = ProductHuntScraper()
        return self._scrapers.get(source)

    async def _fetch_from_source(
        self,
        source: TrendSource,
        limit: int = 25,
    ) -> list[Topic]:
        """Fetch topics from a single source"""
        scraper = self._get_scraper(source)
        if not scraper:
            return []

        try:
            async with scraper:
                return await scraper.fetch_trending(limit=limit)
        except Exception as e:
            print(f"Error fetching from {source.value}: {e}")
            return []

    async def research_trending(
        self,
        limit: int = 25,
        categories: Optional[list[ContentCategory]] = None,
        sources: Optional[list[TrendSource]] = None,
        min_score: float = 30.0,
    ) -> list[Topic]:
        """
        Research trending topics across all configured sources.

        Args:
            limit: Maximum number of topics to return
            categories: Filter by these categories (None = all)
            sources: Override source list for this query
            min_score: Minimum virality score

        Returns:
            Curated list of trending topics
        """
        # Start a research session
        self._session = ResearchSession(
            sources_queried=sources or self.sources,
            filters_applied={"categories": [c.value for c in categories] if categories else [], "min_score": min_score},
        )

        sources_to_query = sources or self.sources
        all_topics = []

        # Fetch from all sources in parallel
        tasks = [
            self._fetch_from_source(source, limit=50)
            for source in sources_to_query
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_topics.extend(result)

        self._session.topics_discovered = len(all_topics)

        # Deduplicate
        all_topics = self.curator.deduplicate_topics(all_topics)

        # Curate and score
        curated = self.curator.curate_topics(
            all_topics,
            limit=limit,
            categories=categories,
            min_score=min_score,
        )

        self._session.topics_curated = len(curated)
        self._session.completed_at = datetime.now(timezone.utc)

        return curated

    async def search(
        self,
        query: str,
        limit: int = 25,
        sources: Optional[list[TrendSource]] = None,
    ) -> list[Topic]:
        """
        Search for topics matching a query across sources.

        Args:
            query: Search query
            limit: Maximum number of results
            sources: Override source list for this query

        Returns:
            List of matching topics
        """
        sources_to_query = sources or self.sources
        all_topics = []

        for source in sources_to_query:
            scraper = self._get_scraper(source)
            if not scraper:
                continue

            try:
                async with scraper:
                    results = await scraper.search(query, limit=25)
                    all_topics.extend(results)
            except Exception as e:
                print(f"Error searching {source.value}: {e}")

        # Deduplicate and curate
        all_topics = self.curator.deduplicate_topics(all_topics)
        curated = self.curator.curate_topics(all_topics, limit=limit, min_score=20.0)

        return curated

    async def research_category(
        self,
        category: ContentCategory,
        limit: int = 25,
    ) -> list[Topic]:
        """
        Research trending topics in a specific category.

        Args:
            category: The category to research
            limit: Maximum number of topics

        Returns:
            List of topics in that category
        """
        # Fetch all trending
        all_topics = await self.research_trending(limit=100, min_score=20.0)

        # Filter by category
        category_topics = [t for t in all_topics if t.category == category]

        return category_topics[:limit]

    async def get_marketing_insights(self, limit: int = 10) -> dict:
        """
        Get high-level marketing insights from trending topics.

        Returns:
            Dictionary with insights including:
            - top_topics: Best viral opportunities
            - trending_keywords: Most mentioned keywords
            - category_breakdown: Topics per category
            - recommendations: Content recommendations
        """
        topics = await self.research_trending(limit=100, min_score=25.0)

        # Get trending keywords
        trending_keywords = self.curator.get_trending_keywords(topics, top_n=15)

        # Group by category
        category_breakdown = self.curator.group_by_category(topics)
        category_counts = {cat.value: len(items) for cat, items in category_breakdown.items()}

        # Top topics
        top_topics = topics[:limit]

        # Generate recommendations
        recommendations = []
        for topic in top_topics[:5]:
            format_type = self.curator.identify_content_format(topic)
            angles = self.curator.generate_content_angles(topic)
            recommendations.append({
                "topic": topic.title,
                "format": format_type,
                "angles": angles[:3],
                "urgency": "high" if topic.virality_score > 70 else "medium",
            })

        return {
            "top_topics": top_topics,
            "trending_keywords": trending_keywords,
            "category_breakdown": category_counts,
            "recommendations": recommendations,
            "session": self._session,
        }

    async def close(self):
        """Close all scraper connections"""
        for scraper in self._scrapers.values():
            try:
                await scraper.close()
            except Exception:
                pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def quick_research(limit: int = 10) -> list[Topic]:
    """
    Quick function to get trending marketing topics.

    Usage:
        topics = await quick_research()
        for topic in topics:
            print(f"{topic.title} - Score: {topic.virality_score}")
    """
    async with ViralContentResearcher() as researcher:
        return await researcher.research_trending(limit=limit)
