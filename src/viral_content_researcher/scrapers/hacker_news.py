"""
Hacker News scraper for tech and startup marketing insights
"""

from datetime import datetime, timezone
from typing import Optional
import asyncio

from viral_content_researcher.scrapers.base import BaseScraper
from viral_content_researcher.models import Topic, TrendSource, ContentCategory


class HackerNewsScraper(BaseScraper):
    """Scraper for Hacker News stories"""

    source = TrendSource.HACKER_NEWS
    base_url = "https://hacker-news.firebaseio.com/v0"

    # Keywords that indicate marketing-relevant content
    MARKETING_KEYWORDS = [
        "marketing", "seo", "growth", "startup", "saas", "b2b",
        "advertising", "ads", "conversion", "analytics", "metrics",
        "customer", "acquisition", "retention", "churn", "viral",
        "social media", "content", "brand", "influencer", "email",
        "newsletter", "audience", "engagement", "traffic", "leads",
        "sales", "revenue", "pricing", "launch", "product hunt",
        "ai", "automation", "personalization", "ecommerce", "shopify",
    ]

    def _categorize_content(self, title: str) -> ContentCategory:
        """Categorize HN story by title"""
        title_lower = title.lower()

        if any(term in title_lower for term in ["seo", "search engine", "google ranking"]):
            return ContentCategory.SEO
        elif any(term in title_lower for term in ["social media", "twitter", "linkedin", "tiktok"]):
            return ContentCategory.SOCIAL_MEDIA
        elif any(term in title_lower for term in ["email", "newsletter"]):
            return ContentCategory.EMAIL_MARKETING
        elif any(term in title_lower for term in ["content", "blog", "writing"]):
            return ContentCategory.CONTENT_MARKETING
        elif any(term in title_lower for term in ["ads", "advertising", "ppc"]):
            return ContentCategory.PAID_ADS
        elif any(term in title_lower for term in ["analytics", "metrics", "data"]):
            return ContentCategory.ANALYTICS
        elif any(term in title_lower for term in ["growth", "viral", "hack"]):
            return ContentCategory.GROWTH_HACKING
        elif any(term in title_lower for term in ["ai", "chatgpt", "llm", "automation"]):
            return ContentCategory.AI_MARKETING
        elif any(term in title_lower for term in ["startup", "launch", "founder"]):
            return ContentCategory.STARTUP
        elif any(term in title_lower for term in ["saas", "b2b", "enterprise"]):
            return ContentCategory.B2B
        elif any(term in title_lower for term in ["ecommerce", "shopify", "amazon"]):
            return ContentCategory.ECOMMERCE

        return ContentCategory.GENERAL

    def _is_marketing_relevant(self, title: str, url: str = "") -> bool:
        """Check if story is relevant to marketing"""
        text = f"{title} {url}".lower()
        return any(kw in text for kw in self.MARKETING_KEYWORDS)

    def _extract_keywords(self, title: str) -> list[str]:
        """Extract keywords from title"""
        found = []
        title_lower = title.lower()

        for kw in self.MARKETING_KEYWORDS:
            if kw in title_lower:
                found.append(kw)

        return found[:10]

    async def _get_story(self, story_id: int) -> Optional[dict]:
        """Fetch a single story by ID"""
        try:
            url = f"{self.base_url}/item/{story_id}.json"
            return await self._fetch(url)
        except Exception:
            return None

    async def fetch_trending(self, limit: int = 25) -> list[Topic]:
        """Fetch top stories from Hacker News"""
        topics = []

        try:
            # Get top story IDs
            url = f"{self.base_url}/topstories.json"
            story_ids = await self._fetch(url)

            # Fetch stories in parallel (batched)
            batch_size = 30
            stories_to_fetch = story_ids[:batch_size * 2]  # Fetch more to filter

            tasks = [self._get_story(sid) for sid in stories_to_fetch]
            stories = await asyncio.gather(*tasks)

            for story in stories:
                if not story or story.get("type") != "story":
                    continue

                title = story.get("title", "")
                story_url = story.get("url", "")

                # Filter for marketing relevance (optional - can be disabled for broader results)
                # is_relevant = self._is_marketing_relevant(title, story_url)

                topic = Topic(
                    id=str(story.get("id")),
                    title=title,
                    description=f"HN discussion with {story.get('descendants', 0)} comments",
                    url=story_url or f"https://news.ycombinator.com/item?id={story.get('id')}",
                    source=TrendSource.HACKER_NEWS,
                    category=self._categorize_content(title),
                    score=story.get("score", 0),
                    comments=story.get("descendants", 0),
                    author=story.get("by"),
                    published_at=datetime.fromtimestamp(
                        story.get("time", 0),
                        tz=timezone.utc
                    ),
                    keywords=self._extract_keywords(title),
                )

                topic.virality_score = self.calculate_virality_score(topic)

                # Boost marketing-relevant content
                if self._is_marketing_relevant(title, story_url):
                    topic.virality_score = min(topic.virality_score * 1.3, 100)

                topics.append(topic)

            # Sort by virality score
            topics.sort(key=lambda x: x.virality_score, reverse=True)

        except Exception as e:
            print(f"Error fetching HN stories: {e}")

        return topics[:limit]

    async def fetch_new(self, limit: int = 25) -> list[Topic]:
        """Fetch newest stories from Hacker News"""
        topics = []

        try:
            url = f"{self.base_url}/newstories.json"
            story_ids = await self._fetch(url)

            tasks = [self._get_story(sid) for sid in story_ids[:limit * 2]]
            stories = await asyncio.gather(*tasks)

            for story in stories:
                if not story or story.get("type") != "story":
                    continue

                title = story.get("title", "")
                story_url = story.get("url", "")

                topic = Topic(
                    id=str(story.get("id")),
                    title=title,
                    url=story_url or f"https://news.ycombinator.com/item?id={story.get('id')}",
                    source=TrendSource.HACKER_NEWS,
                    category=self._categorize_content(title),
                    score=story.get("score", 0),
                    comments=story.get("descendants", 0),
                    author=story.get("by"),
                    published_at=datetime.fromtimestamp(
                        story.get("time", 0),
                        tz=timezone.utc
                    ),
                    keywords=self._extract_keywords(title),
                )

                topic.virality_score = self.calculate_virality_score(topic)
                topics.append(topic)

        except Exception as e:
            print(f"Error fetching new HN stories: {e}")

        return topics[:limit]

    async def search(self, query: str, limit: int = 25) -> list[Topic]:
        """Search Hacker News using Algolia API"""
        topics = []

        try:
            # Use HN Algolia Search API
            url = "https://hn.algolia.com/api/v1/search"
            params = {
                "query": query,
                "tags": "story",
                "hitsPerPage": limit,
            }

            session = await self.get_session()
            async with session.get(url, params=params) as response:
                data = await response.json()

            for hit in data.get("hits", []):
                title = hit.get("title", "")

                topic = Topic(
                    id=str(hit.get("objectID")),
                    title=title,
                    description=f"Search result for '{query}'",
                    url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    source=TrendSource.HACKER_NEWS,
                    category=self._categorize_content(title),
                    score=hit.get("points", 0),
                    comments=hit.get("num_comments", 0),
                    author=hit.get("author"),
                    published_at=datetime.fromisoformat(
                        hit.get("created_at", "").replace("Z", "+00:00")
                    ) if hit.get("created_at") else None,
                    keywords=self._extract_keywords(title),
                )

                topic.virality_score = self.calculate_virality_score(topic)
                topics.append(topic)

        except Exception as e:
            print(f"Error searching HN: {e}")

        return topics

    async def fetch_show_hn(self, limit: int = 25) -> list[Topic]:
        """Fetch Show HN stories (product launches)"""
        topics = []

        try:
            url = f"{self.base_url}/showstories.json"
            story_ids = await self._fetch(url)

            tasks = [self._get_story(sid) for sid in story_ids[:limit * 2]]
            stories = await asyncio.gather(*tasks)

            for story in stories:
                if not story:
                    continue

                title = story.get("title", "")
                story_url = story.get("url", "")

                topic = Topic(
                    id=str(story.get("id")),
                    title=title,
                    description="Show HN - Product/Project Launch",
                    url=story_url or f"https://news.ycombinator.com/item?id={story.get('id')}",
                    source=TrendSource.HACKER_NEWS,
                    category=ContentCategory.STARTUP,
                    score=story.get("score", 0),
                    comments=story.get("descendants", 0),
                    author=story.get("by"),
                    published_at=datetime.fromtimestamp(
                        story.get("time", 0),
                        tz=timezone.utc
                    ),
                    keywords=self._extract_keywords(title) + ["show hn", "launch"],
                )

                topic.virality_score = self.calculate_virality_score(topic)
                topics.append(topic)

        except Exception as e:
            print(f"Error fetching Show HN: {e}")

        return topics[:limit]
