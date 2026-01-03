"""
Product Hunt scraper for marketing tools and trending products
"""

from datetime import datetime, timezone
from typing import Optional
from bs4 import BeautifulSoup

from viral_content_researcher.scrapers.base import BaseScraper
from viral_content_researcher.models import Topic, TrendSource, ContentCategory


class ProductHuntScraper(BaseScraper):
    """Scraper for Product Hunt launches"""

    source = TrendSource.PRODUCT_HUNT
    base_url = "https://www.producthunt.com"

    # Marketing-related product categories
    MARKETING_CATEGORIES = [
        "marketing",
        "seo",
        "social-media-tools",
        "email-marketing",
        "analytics",
        "advertising",
        "growth-hacking",
        "sales",
        "productivity",
        "ai",
        "automation",
        "ecommerce",
        "writing-tools",
        "design-tools",
        "video",
    ]

    def _get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def _categorize_product(self, name: str, tagline: str, topics: list[str]) -> ContentCategory:
        """Categorize a product based on its info"""
        text = f"{name} {tagline} {' '.join(topics)}".lower()

        if any(term in text for term in ["seo", "search engine", "ranking", "backlink"]):
            return ContentCategory.SEO
        elif any(term in text for term in ["social media", "instagram", "tiktok", "twitter", "linkedin"]):
            return ContentCategory.SOCIAL_MEDIA
        elif any(term in text for term in ["email", "newsletter", "outreach"]):
            return ContentCategory.EMAIL_MARKETING
        elif any(term in text for term in ["content", "blog", "writing", "copywriting"]):
            return ContentCategory.CONTENT_MARKETING
        elif any(term in text for term in ["ads", "advertising", "ppc", "campaign"]):
            return ContentCategory.PAID_ADS
        elif any(term in text for term in ["analytics", "metrics", "data", "dashboard"]):
            return ContentCategory.ANALYTICS
        elif any(term in text for term in ["growth", "viral", "acquisition"]):
            return ContentCategory.GROWTH_HACKING
        elif any(term in text for term in ["influencer", "creator", "ugc"]):
            return ContentCategory.INFLUENCER
        elif any(term in text for term in ["video", "youtube", "reels"]):
            return ContentCategory.VIDEO_MARKETING
        elif any(term in text for term in ["ai", "chatgpt", "automation", "gpt"]):
            return ContentCategory.AI_MARKETING
        elif any(term in text for term in ["ecommerce", "shopify", "store", "commerce"]):
            return ContentCategory.ECOMMERCE
        elif any(term in text for term in ["saas", "b2b", "enterprise"]):
            return ContentCategory.B2B

        return ContentCategory.STARTUP

    def _extract_keywords(self, name: str, tagline: str) -> list[str]:
        """Extract keywords from product info"""
        text = f"{name} {tagline}".lower()

        marketing_keywords = [
            "ai", "automation", "marketing", "seo", "analytics",
            "social media", "email", "content", "sales", "leads",
            "conversion", "growth", "engagement", "productivity",
            "writing", "video", "design", "ecommerce", "startup",
        ]

        found = []
        for kw in marketing_keywords:
            if kw in text:
                found.append(kw)

        return found[:10]

    async def fetch_trending(self, limit: int = 25) -> list[Topic]:
        """Fetch today's top products from Product Hunt"""
        topics = []

        try:
            # Fetch the homepage
            html = await self._fetch_html(self.base_url)
            soup = BeautifulSoup(html, 'html.parser')

            # Find product cards (structure may change, this is a best effort)
            # Look for common product list patterns
            product_sections = soup.find_all(['div', 'article'], attrs={'data-test': True})

            if not product_sections:
                # Fallback: look for links that look like product pages
                product_links = soup.find_all('a', href=lambda x: x and '/posts/' in x)

                for idx, link in enumerate(product_links[:limit]):
                    href = link.get('href', '')
                    if not href.startswith('http'):
                        href = f"{self.base_url}{href}"

                    # Extract text content
                    title = link.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue

                    topic = Topic(
                        id=f"ph_{idx}",
                        title=title[:200],
                        description="Product Hunt launch",
                        url=href,
                        source=TrendSource.PRODUCT_HUNT,
                        category=ContentCategory.STARTUP,
                        published_at=datetime.now(timezone.utc),
                        keywords=self._extract_keywords(title, ""),
                    )

                    topic.virality_score = 60 - (idx * 2)  # Higher rank = higher score
                    topics.append(topic)

        except Exception as e:
            print(f"Error fetching Product Hunt: {e}")

        # Deduplicate by URL
        seen_urls = set()
        unique_topics = []
        for topic in topics:
            if topic.url not in seen_urls:
                seen_urls.add(topic.url)
                unique_topics.append(topic)

        return unique_topics[:limit]

    async def search(self, query: str, limit: int = 25) -> list[Topic]:
        """Search Product Hunt for products"""
        topics = []

        try:
            search_url = f"{self.base_url}/search"
            params = {"q": query}

            html = await self._fetch_html(search_url, params)
            soup = BeautifulSoup(html, 'html.parser')

            # Find search results
            result_links = soup.find_all('a', href=lambda x: x and '/posts/' in x)

            for idx, link in enumerate(result_links[:limit]):
                href = link.get('href', '')
                if not href.startswith('http'):
                    href = f"{self.base_url}{href}"

                title = link.get_text(strip=True)
                if not title or len(title) < 3:
                    continue

                topic = Topic(
                    id=f"ph_search_{idx}",
                    title=title[:200],
                    description=f"Search result for '{query}'",
                    url=href,
                    source=TrendSource.PRODUCT_HUNT,
                    category=self._categorize_product(title, query, []),
                    keywords=self._extract_keywords(title, query),
                )

                topic.virality_score = 50
                topics.append(topic)

        except Exception as e:
            print(f"Error searching Product Hunt: {e}")

        return topics

    async def fetch_category(self, category: str, limit: int = 25) -> list[Topic]:
        """Fetch products from a specific category"""
        topics = []

        try:
            category_url = f"{self.base_url}/topics/{category}"
            html = await self._fetch_html(category_url)
            soup = BeautifulSoup(html, 'html.parser')

            product_links = soup.find_all('a', href=lambda x: x and '/posts/' in x)

            for idx, link in enumerate(product_links[:limit]):
                href = link.get('href', '')
                if not href.startswith('http'):
                    href = f"{self.base_url}{href}"

                title = link.get_text(strip=True)
                if not title or len(title) < 3:
                    continue

                topic = Topic(
                    id=f"ph_cat_{category}_{idx}",
                    title=title[:200],
                    description=f"Product in {category} category",
                    url=href,
                    source=TrendSource.PRODUCT_HUNT,
                    category=self._categorize_product(title, category, [category]),
                    keywords=self._extract_keywords(title, category),
                )

                topic.virality_score = 55 - (idx * 2)
                topics.append(topic)

        except Exception as e:
            print(f"Error fetching PH category {category}: {e}")

        return topics

    async def fetch_marketing_tools(self, limit: int = 25) -> list[Topic]:
        """Fetch marketing-related tools from Product Hunt"""
        all_topics = []

        # Fetch from multiple marketing-related categories
        for category in self.MARKETING_CATEGORIES[:5]:  # Limit to avoid rate limiting
            try:
                category_topics = await self.fetch_category(category, limit=5)
                all_topics.extend(category_topics)
            except Exception:
                continue

        # Sort by virality score
        all_topics.sort(key=lambda x: x.virality_score, reverse=True)

        return all_topics[:limit]
