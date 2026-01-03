"""
Data models for the viral content research system
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TrendSource(str, Enum):
    """Sources for trending content"""
    REDDIT = "reddit"
    GOOGLE_TRENDS = "google_trends"
    HACKER_NEWS = "hacker_news"
    PRODUCT_HUNT = "product_hunt"
    RSS_FEED = "rss_feed"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    NEWS_API = "news_api"


class ContentCategory(str, Enum):
    """Marketing content categories"""
    SEO = "seo"
    SOCIAL_MEDIA = "social_media"
    EMAIL_MARKETING = "email_marketing"
    CONTENT_MARKETING = "content_marketing"
    PAID_ADS = "paid_ads"
    ANALYTICS = "analytics"
    BRANDING = "branding"
    GROWTH_HACKING = "growth_hacking"
    INFLUENCER = "influencer"
    VIDEO_MARKETING = "video_marketing"
    AI_MARKETING = "ai_marketing"
    ECOMMERCE = "ecommerce"
    B2B = "b2b"
    STARTUP = "startup"
    GENERAL = "general"


class Topic(BaseModel):
    """Represents a trending topic"""
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    source: TrendSource
    category: ContentCategory = ContentCategory.GENERAL

    # Engagement metrics
    score: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0

    # Virality scoring
    virality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    trending_velocity: float = 0.0  # How fast it's growing

    # Metadata
    keywords: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    author: Optional[str] = None

    # Timestamps
    published_at: Optional[datetime] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    # Content potential
    content_angle: Optional[str] = None
    target_audience: Optional[str] = None


class ContentBrief(BaseModel):
    """A content brief generated from trending topics"""
    id: Optional[str] = None
    title: str
    hook: str
    outline: list[str]

    # Source topics
    source_topics: list[Topic] = Field(default_factory=list)

    # Content details
    suggested_format: str = "blog_post"  # blog_post, video, infographic, thread, etc.
    estimated_word_count: int = 1500
    target_keywords: list[str] = Field(default_factory=list)

    # SEO
    meta_description: Optional[str] = None
    suggested_title_variants: list[str] = Field(default_factory=list)

    # Metadata
    category: ContentCategory = ContentCategory.GENERAL
    urgency: str = "medium"  # low, medium, high, trending_now
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Notes
    notes: Optional[str] = None
    competitors: list[str] = Field(default_factory=list)


class ResearchSession(BaseModel):
    """A research session tracking discovered topics"""
    id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    topics_discovered: int = 0
    topics_curated: int = 0
    briefs_generated: int = 0

    sources_queried: list[TrendSource] = Field(default_factory=list)
    filters_applied: dict = Field(default_factory=dict)


class SourceConfig(BaseModel):
    """Configuration for a data source"""
    source: TrendSource
    enabled: bool = True
    api_key: Optional[str] = None
    rate_limit: int = 60  # requests per minute
    custom_params: dict = Field(default_factory=dict)
