"""
Content brief generator for creating actionable content plans
"""

from datetime import datetime
from typing import Optional
import uuid

from viral_content_researcher.models import Topic, ContentBrief, ContentCategory
from viral_content_researcher.curator import ContentCurator


class BriefGenerator:
    """
    Generates content briefs from trending topics.
    Creates actionable plans for content creation.
    """

    # Content format templates
    FORMAT_TEMPLATES = {
        "blog_post": {
            "sections": ["Introduction", "Main Points", "Examples", "Conclusion", "CTA"],
            "word_count": 1500,
        },
        "guide": {
            "sections": ["Introduction", "Prerequisites", "Step-by-Step Guide", "Pro Tips", "Common Mistakes", "Conclusion"],
            "word_count": 2500,
        },
        "listicle": {
            "sections": ["Introduction", "List Items (7-10)", "Bonus Tips", "Conclusion"],
            "word_count": 1500,
        },
        "tutorial": {
            "sections": ["Overview", "What You'll Learn", "Step 1", "Step 2", "Step 3", "Testing", "Troubleshooting"],
            "word_count": 2000,
        },
        "comparison": {
            "sections": ["Introduction", "Overview of Options", "Feature Comparison", "Pros and Cons", "Verdict", "Recommendation"],
            "word_count": 1800,
        },
        "case_study": {
            "sections": ["Executive Summary", "Background", "Challenge", "Solution", "Results", "Lessons Learned"],
            "word_count": 2000,
        },
        "review": {
            "sections": ["Introduction", "Overview", "Features", "Pros", "Cons", "Pricing", "Verdict"],
            "word_count": 1200,
        },
        "strategy_guide": {
            "sections": ["Executive Summary", "Current Landscape", "Strategy Framework", "Implementation", "Metrics", "Next Steps"],
            "word_count": 3000,
        },
    }

    # Hook templates by category
    HOOK_TEMPLATES = {
        ContentCategory.SEO: [
            "Here's the SEO strategy that generated {X}% more organic traffic",
            "The {topic} technique top sites use (and you should too)",
            "Why {topic} is the key to ranking higher in 2025",
        ],
        ContentCategory.SOCIAL_MEDIA: [
            "How {topic} is changing social media marketing forever",
            "The viral {topic} strategy that grew our audience 10x",
            "{topic}: The social media secret brands don't want you to know",
        ],
        ContentCategory.CONTENT_MARKETING: [
            "The {topic} framework that converts readers into customers",
            "Content marketing breakthrough: How {topic} drives engagement",
            "Why {topic} is the future of content strategy",
        ],
        ContentCategory.GROWTH_HACKING: [
            "Growth hack: How {topic} can 10x your results",
            "The unconventional {topic} strategy that went viral",
            "{topic} - The growth lever you're probably ignoring",
        ],
        ContentCategory.AI_MARKETING: [
            "How AI is revolutionizing {topic} for marketers",
            "The {topic} AI tool that's changing everything",
            "{topic} + AI: The marketing combo you need to try",
        ],
        ContentCategory.STARTUP: [
            "Startup lessons: How {topic} led to product-market fit",
            "The {topic} strategy every founder should know",
            "From 0 to 1: How {topic} transformed our startup",
        ],
    }

    def __init__(self, curator: Optional[ContentCurator] = None):
        self.curator = curator or ContentCurator()

    def _generate_hook(self, topic: Topic) -> str:
        """Generate an engaging hook for the content"""
        templates = self.HOOK_TEMPLATES.get(
            topic.category,
            ["Discover how {topic} can transform your marketing strategy"]
        )

        # Use first template (could randomize)
        hook = templates[0].replace("{topic}", topic.title)
        hook = hook.replace("{X}", "250")  # Placeholder number

        return hook

    def _generate_outline(self, topic: Topic, format_type: str) -> list[str]:
        """Generate a content outline"""
        template = self.FORMAT_TEMPLATES.get(format_type, self.FORMAT_TEMPLATES["blog_post"])
        base_sections = template["sections"].copy()

        # Customize based on topic
        outline = []
        for section in base_sections:
            if "List Items" in section:
                # Generate list items
                outline.append(f"## {section}")
                for i in range(7):
                    outline.append(f"  - Item {i+1}: [Related to {topic.title}]")
            elif "Step" in section and section != "Step-by-Step Guide":
                outline.append(f"## {section}: [Action related to {topic.title}]")
            else:
                outline.append(f"## {section}")

        return outline

    def _extract_target_keywords(self, topic: Topic) -> list[str]:
        """Extract target keywords from topic"""
        keywords = topic.keywords.copy() if topic.keywords else []

        # Add topic title words
        title_words = topic.title.lower().split()
        for word in title_words:
            if len(word) > 3 and word not in keywords:
                keywords.append(word)

        return keywords[:10]

    def _generate_title_variants(self, topic: Topic, format_type: str) -> list[str]:
        """Generate alternative title options"""
        base_title = topic.title

        variants = [
            f"How to Master {base_title} in 2025",
            f"The Complete Guide to {base_title}",
            f"{base_title}: Everything You Need to Know",
            f"Why {base_title} Matters (And How to Get Started)",
            f"Top 10 {base_title} Strategies That Actually Work",
            f"{base_title} Explained: A Marketer's Guide",
            f"The Ultimate {base_title} Playbook",
        ]

        # Add format-specific variants
        if format_type == "listicle":
            variants.extend([
                f"7 {base_title} Tips You Need to Know",
                f"10 {base_title} Mistakes to Avoid",
            ])
        elif format_type == "tutorial":
            variants.extend([
                f"Step-by-Step: {base_title} Tutorial for Beginners",
                f"How to {base_title}: A Complete Walkthrough",
            ])
        elif format_type == "case_study":
            variants.extend([
                f"Case Study: How {base_title} Drove Results",
                f"Real Results: Our {base_title} Journey",
            ])

        return variants[:5]

    def _generate_meta_description(self, topic: Topic, hook: str) -> str:
        """Generate SEO meta description"""
        # Keep under 160 characters
        desc = f"Learn {topic.title.lower()}. {hook[:80]}"
        if len(desc) > 155:
            desc = desc[:152] + "..."
        return desc

    def _determine_urgency(self, topic: Topic) -> str:
        """Determine content urgency based on topic metrics"""
        if topic.virality_score >= 80:
            return "trending_now"
        elif topic.virality_score >= 60:
            return "high"
        elif topic.virality_score >= 40:
            return "medium"
        else:
            return "low"

    def generate_brief(
        self,
        topic: Topic,
        format_type: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ContentBrief:
        """
        Generate a content brief from a topic.

        Args:
            topic: The source topic
            format_type: Override content format (auto-detected if None)
            notes: Additional notes for the brief

        Returns:
            ContentBrief ready for content creation
        """
        # Determine format
        if not format_type:
            format_type = self.curator.identify_content_format(topic)

        template = self.FORMAT_TEMPLATES.get(format_type, self.FORMAT_TEMPLATES["blog_post"])

        # Generate components
        hook = self._generate_hook(topic)
        outline = self._generate_outline(topic, format_type)
        keywords = self._extract_target_keywords(topic)
        title_variants = self._generate_title_variants(topic, format_type)
        meta_desc = self._generate_meta_description(topic, hook)
        urgency = self._determine_urgency(topic)

        # Create brief
        brief = ContentBrief(
            id=str(uuid.uuid4()),
            title=f"Content Brief: {topic.title}",
            hook=hook,
            outline=outline,
            source_topics=[topic],
            suggested_format=format_type,
            estimated_word_count=template["word_count"],
            target_keywords=keywords,
            meta_description=meta_desc,
            suggested_title_variants=title_variants,
            category=topic.category,
            urgency=urgency,
            notes=notes,
            created_at=datetime.utcnow(),
        )

        return brief

    def generate_briefs_from_topics(
        self,
        topics: list[Topic],
        limit: int = 5,
    ) -> list[ContentBrief]:
        """
        Generate multiple content briefs from top topics.

        Args:
            topics: List of topics (will use highest scored)
            limit: Maximum number of briefs to generate

        Returns:
            List of content briefs
        """
        # Sort by virality score
        sorted_topics = sorted(topics, key=lambda x: x.virality_score, reverse=True)

        briefs = []
        for topic in sorted_topics[:limit]:
            brief = self.generate_brief(topic)
            briefs.append(brief)

        return briefs

    def generate_content_calendar(
        self,
        topics: list[Topic],
        days: int = 7,
    ) -> list[dict]:
        """
        Generate a content calendar from topics.

        Args:
            topics: List of topics
            days: Number of days to plan

        Returns:
            List of calendar entries with dates and briefs
        """
        from datetime import timedelta

        calendar = []
        sorted_topics = sorted(topics, key=lambda x: x.virality_score, reverse=True)

        today = datetime.utcnow().date()

        for i in range(min(days, len(sorted_topics))):
            topic = sorted_topics[i]
            brief = self.generate_brief(topic)

            publish_date = today + timedelta(days=i)

            calendar.append({
                "date": publish_date.isoformat(),
                "day_of_week": publish_date.strftime("%A"),
                "topic": topic.title,
                "format": brief.suggested_format,
                "urgency": brief.urgency,
                "brief": brief,
                "estimated_time": f"{brief.estimated_word_count // 500} hours",
            })

        return calendar

    def format_brief_as_markdown(self, brief: ContentBrief) -> str:
        """Format a content brief as markdown"""
        md = []

        md.append(f"# {brief.title}")
        md.append("")
        md.append(f"**Format:** {brief.suggested_format}")
        md.append(f"**Word Count:** ~{brief.estimated_word_count} words")
        md.append(f"**Urgency:** {brief.urgency}")
        md.append(f"**Category:** {brief.category.value}")
        md.append("")

        md.append("## Hook")
        md.append(brief.hook)
        md.append("")

        md.append("## Title Options")
        for variant in brief.suggested_title_variants:
            md.append(f"- {variant}")
        md.append("")

        md.append("## Target Keywords")
        md.append(", ".join(brief.target_keywords))
        md.append("")

        md.append("## Meta Description")
        md.append(brief.meta_description or "")
        md.append("")

        md.append("## Outline")
        for section in brief.outline:
            md.append(section)
        md.append("")

        if brief.notes:
            md.append("## Notes")
            md.append(brief.notes)
            md.append("")

        if brief.source_topics:
            md.append("## Source Topics")
            for topic in brief.source_topics:
                md.append(f"- [{topic.title}]({topic.url}) (Score: {topic.virality_score})")

        return "\n".join(md)
