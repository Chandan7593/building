"""
Data source scrapers for trending content
"""

from viral_content_researcher.scrapers.base import BaseScraper
from viral_content_researcher.scrapers.reddit import RedditScraper
from viral_content_researcher.scrapers.google_trends import GoogleTrendsScraper
from viral_content_researcher.scrapers.hacker_news import HackerNewsScraper
from viral_content_researcher.scrapers.rss_feeds import RSSFeedScraper
from viral_content_researcher.scrapers.product_hunt import ProductHuntScraper

__all__ = [
    "BaseScraper",
    "RedditScraper",
    "GoogleTrendsScraper",
    "HackerNewsScraper",
    "RSSFeedScraper",
    "ProductHuntScraper",
]
