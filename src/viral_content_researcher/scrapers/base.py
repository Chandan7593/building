"""
Base scraper class for all data sources
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from viral_content_researcher.models import Topic, TrendSource


class BaseScraper(ABC):
    """Base class for all content scrapers"""

    source: TrendSource
    base_url: str = ""

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit: int = 60,
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.rate_limit = rate_limit
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_count = 0
        self._last_reset = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._get_headers(),
            )
        return self._session

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_headers(self) -> dict:
        """Get default headers for requests"""
        return {
            "User-Agent": "ViralContentResearcher/1.0 (Marketing Research Tool)",
            "Accept": "application/json",
        }

    async def _check_rate_limit(self):
        """Simple rate limiting"""
        loop = asyncio.get_event_loop()
        current_time = loop.time()

        if current_time - self._last_reset >= 60:
            self._request_count = 0
            self._last_reset = current_time

        if self._request_count >= self.rate_limit:
            wait_time = 60 - (current_time - self._last_reset)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._request_count = 0
            self._last_reset = loop.time()

        self._request_count += 1

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _fetch(self, url: str, params: Optional[dict] = None) -> dict:
        """Fetch data from URL with retry logic"""
        await self._check_rate_limit()
        session = await self.get_session()

        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _fetch_html(self, url: str, params: Optional[dict] = None) -> str:
        """Fetch HTML content from URL"""
        await self._check_rate_limit()
        session = await self.get_session()

        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.text()

    @abstractmethod
    async def fetch_trending(self, limit: int = 25) -> list[Topic]:
        """Fetch trending topics from this source"""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 25) -> list[Topic]:
        """Search for topics matching query"""
        pass

    def calculate_virality_score(self, topic: Topic) -> float:
        """Calculate a virality score based on engagement metrics"""
        # Base score from upvotes/score
        base_score = min(topic.score / 100, 30)

        # Comment engagement (comments indicate discussion)
        comment_score = min(topic.comments / 50, 25)

        # Shares indicate viral potential
        share_score = min(topic.shares / 20, 25)

        # Recency bonus (newer = more relevant)
        recency_score = 0
        if topic.published_at:
            from datetime import datetime, timezone
            hours_old = (datetime.now(timezone.utc) - topic.published_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            if hours_old < 6:
                recency_score = 20
            elif hours_old < 24:
                recency_score = 15
            elif hours_old < 48:
                recency_score = 10
            elif hours_old < 72:
                recency_score = 5

        return min(base_score + comment_score + share_score + recency_score, 100)

    async def __aenter__(self):
        await self.get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
