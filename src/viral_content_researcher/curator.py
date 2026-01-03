"""
Content curation and scoring engine for viral marketing topics
"""

from datetime import datetime, timezone
from typing import Optional
import re

from viral_content_researcher.models import Topic, ContentCategory, ContentBrief


class ContentCurator:
    """
    Curates and scores topics for viral potential and marketing relevance.
    Uses multiple signals to identify high-value content opportunities.
    """

    # Weighted scoring factors
    WEIGHTS = {
        "engagement": 0.25,
        "recency": 0.20,
        "relevance": 0.25,
        "velocity": 0.15,
        "uniqueness": 0.15,
    }

    # High-value marketing keywords (boost score)
    HIGH_VALUE_KEYWORDS = [
        "ai", "chatgpt", "automation", "no-code", "growth",
        "viral", "10x", "secret", "strategy", "hack",
        "free", "tool", "template", "guide", "case study",
        "revenue", "million", "scaling", "framework", "playbook",
    ]

    # Trending topic indicators
    TRENDING_INDICATORS = [
        "just launched", "new", "breaking", "update", "2024", "2025",
        "announcement", "release", "introducing", "first",
    ]

    # Content format preferences (for brief generation)
    FORMAT_KEYWORDS = {
        "how to": "tutorial",
        "guide": "guide",
        "list": "listicle",
        "vs": "comparison",
        "review": "review",
        "case study": "case_study",
        "template": "template",
        "tool": "tool_review",
        "tips": "listicle",
        "mistakes": "listicle",
        "secrets": "listicle",
        "strategy": "strategy_guide",
    }

    def __init__(
        self,
        min_score: float = 30.0,
        max_age_hours: int = 72,
        boost_categories: Optional[list[ContentCategory]] = None,
    ):
        self.min_score = min_score
        self.max_age_hours = max_age_hours
        self.boost_categories = boost_categories or [
            ContentCategory.AI_MARKETING,
            ContentCategory.GROWTH_HACKING,
            ContentCategory.SEO,
        ]

    def calculate_engagement_score(self, topic: Topic) -> float:
        """Calculate normalized engagement score (0-100)"""
        # Weighted engagement metrics
        score = 0

        # Upvotes/score (different scales for different sources)
        if topic.score > 0:
            score += min(topic.score / 50, 40)

        # Comments indicate discussion quality
        if topic.comments > 0:
            score += min(topic.comments / 25, 30)

        # Shares indicate viral potential
        if topic.shares > 0:
            score += min(topic.shares / 10, 30)

        return min(score, 100)

    def calculate_recency_score(self, topic: Topic) -> float:
        """Calculate recency score - newer content scores higher"""
        if not topic.published_at:
            return 30  # Unknown date gets middle score

        now = datetime.now(timezone.utc)
        published = topic.published_at.replace(tzinfo=timezone.utc) if topic.published_at.tzinfo is None else topic.published_at

        hours_old = (now - published).total_seconds() / 3600

        if hours_old < 2:
            return 100
        elif hours_old < 6:
            return 90
        elif hours_old < 12:
            return 80
        elif hours_old < 24:
            return 70
        elif hours_old < 48:
            return 50
        elif hours_old < 72:
            return 30
        else:
            return 10

    def calculate_relevance_score(self, topic: Topic) -> float:
        """Calculate marketing relevance score"""
        score = 50  # Base score

        title_lower = topic.title.lower()
        desc_lower = (topic.description or "").lower()
        text = f"{title_lower} {desc_lower}"

        # Boost for high-value keywords
        keyword_matches = sum(1 for kw in self.HIGH_VALUE_KEYWORDS if kw in text)
        score += min(keyword_matches * 5, 30)

        # Boost for trending indicators
        trending_matches = sum(1 for ind in self.TRENDING_INDICATORS if ind in text)
        score += min(trending_matches * 5, 15)

        # Boost for preferred categories
        if topic.category in self.boost_categories:
            score += 10

        # Boost if has good keywords
        if topic.keywords:
            score += min(len(topic.keywords) * 2, 10)

        return min(score, 100)

    def calculate_velocity_score(self, topic: Topic) -> float:
        """Estimate trending velocity - how fast is this topic growing"""
        if topic.trending_velocity > 0:
            return min(topic.trending_velocity, 100)

        # Estimate based on engagement relative to age
        if not topic.published_at:
            return 40

        now = datetime.now(timezone.utc)
        published = topic.published_at.replace(tzinfo=timezone.utc) if topic.published_at.tzinfo is None else topic.published_at
        hours_old = max((now - published).total_seconds() / 3600, 1)

        # Engagement per hour
        engagement_rate = (topic.score + topic.comments * 2) / hours_old

        if engagement_rate > 50:
            return 100
        elif engagement_rate > 25:
            return 80
        elif engagement_rate > 10:
            return 60
        elif engagement_rate > 5:
            return 40
        else:
            return 20

    def calculate_uniqueness_score(self, topic: Topic, existing_topics: list[Topic] = None) -> float:
        """Calculate how unique this topic is compared to others"""
        if not existing_topics:
            return 70  # Default when no comparison available

        title_words = set(topic.title.lower().split())

        # Check overlap with existing topics
        max_overlap = 0
        for existing in existing_topics:
            if existing.id == topic.id:
                continue
            existing_words = set(existing.title.lower().split())
            overlap = len(title_words & existing_words) / max(len(title_words), 1)
            max_overlap = max(max_overlap, overlap)

        # High overlap = low uniqueness
        return max(100 - (max_overlap * 100), 10)

    def score_topic(self, topic: Topic, existing_topics: list[Topic] = None) -> float:
        """Calculate comprehensive virality score for a topic"""
        scores = {
            "engagement": self.calculate_engagement_score(topic),
            "recency": self.calculate_recency_score(topic),
            "relevance": self.calculate_relevance_score(topic),
            "velocity": self.calculate_velocity_score(topic),
            "uniqueness": self.calculate_uniqueness_score(topic, existing_topics),
        }

        # Weighted average
        final_score = sum(
            scores[key] * self.WEIGHTS[key]
            for key in scores
        )

        return round(final_score, 2)

    def curate_topics(
        self,
        topics: list[Topic],
        limit: int = 25,
        categories: Optional[list[ContentCategory]] = None,
        min_score: Optional[float] = None,
    ) -> list[Topic]:
        """
        Curate and rank topics by viral potential.

        Args:
            topics: List of topics to curate
            limit: Maximum number of topics to return
            categories: Filter by these categories (None = all)
            min_score: Minimum virality score (uses instance default if None)

        Returns:
            Curated list of topics sorted by score
        """
        min_score = min_score if min_score is not None else self.min_score

        # Filter by category if specified
        if categories:
            topics = [t for t in topics if t.category in categories]

        # Filter by age
        now = datetime.now(timezone.utc)
        topics = [
            t for t in topics
            if not t.published_at or
            (now - t.published_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600 <= self.max_age_hours
        ]

        # Score all topics
        for topic in topics:
            topic.virality_score = self.score_topic(topic, topics)

        # Filter by minimum score
        topics = [t for t in topics if t.virality_score >= min_score]

        # Sort by virality score
        topics.sort(key=lambda x: x.virality_score, reverse=True)

        return topics[:limit]

    def deduplicate_topics(self, topics: list[Topic], similarity_threshold: float = 0.6) -> list[Topic]:
        """Remove duplicate or very similar topics"""
        unique_topics = []

        for topic in topics:
            is_duplicate = False
            title_words = set(topic.title.lower().split())

            for existing in unique_topics:
                existing_words = set(existing.title.lower().split())
                overlap = len(title_words & existing_words) / max(len(title_words | existing_words), 1)

                if overlap >= similarity_threshold:
                    is_duplicate = True
                    # Keep the higher-scoring one
                    if topic.virality_score > existing.virality_score:
                        unique_topics.remove(existing)
                        unique_topics.append(topic)
                    break

            if not is_duplicate:
                unique_topics.append(topic)

        return unique_topics

    def identify_content_format(self, topic: Topic) -> str:
        """Suggest the best content format for a topic"""
        title_lower = topic.title.lower()

        for keyword, format_type in self.FORMAT_KEYWORDS.items():
            if keyword in title_lower:
                return format_type

        # Default based on category
        category_formats = {
            ContentCategory.SEO: "guide",
            ContentCategory.SOCIAL_MEDIA: "listicle",
            ContentCategory.CONTENT_MARKETING: "guide",
            ContentCategory.ANALYTICS: "tutorial",
            ContentCategory.AI_MARKETING: "tool_review",
            ContentCategory.STARTUP: "case_study",
        }

        return category_formats.get(topic.category, "blog_post")

    def generate_content_angles(self, topic: Topic) -> list[str]:
        """Generate potential content angles for a topic"""
        angles = []
        title = topic.title

        # Standard content angles
        angles.append(f"How to {title.lower()} - Complete Guide")
        angles.append(f"Why {title} Matters in 2025")
        angles.append(f"Top 10 {title} Strategies That Work")
        angles.append(f"{title} vs Traditional Methods: A Comparison")
        angles.append(f"The Ultimate {title} Playbook for Marketers")
        angles.append(f"Case Study: How We Achieved {title}")
        angles.append(f"Common {title} Mistakes to Avoid")
        angles.append(f"Future of {title}: Trends and Predictions")

        return angles

    def estimate_word_count(self, format_type: str) -> int:
        """Estimate recommended word count for content format"""
        word_counts = {
            "listicle": 1500,
            "guide": 2500,
            "tutorial": 2000,
            "comparison": 1800,
            "review": 1200,
            "case_study": 2000,
            "template": 1000,
            "tool_review": 1500,
            "strategy_guide": 3000,
            "blog_post": 1500,
        }
        return word_counts.get(format_type, 1500)

    def group_by_category(self, topics: list[Topic]) -> dict[ContentCategory, list[Topic]]:
        """Group topics by their category"""
        grouped = {}
        for topic in topics:
            if topic.category not in grouped:
                grouped[topic.category] = []
            grouped[topic.category].append(topic)
        return grouped

    def get_trending_keywords(self, topics: list[Topic], top_n: int = 20) -> list[tuple[str, int]]:
        """Extract most common keywords from topics"""
        keyword_counts = {}

        for topic in topics:
            for kw in topic.keywords:
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        # Sort by count
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_keywords[:top_n]
