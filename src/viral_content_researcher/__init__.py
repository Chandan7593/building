"""
Viral Content Researcher - Find and curate trending marketing topics
"""

__version__ = "1.0.0"
__author__ = "Marketing Content Team"

from viral_content_researcher.models import Topic, ContentBrief, TrendSource
from viral_content_researcher.researcher import ViralContentResearcher
from viral_content_researcher.curator import ContentCurator

__all__ = [
    "Topic",
    "ContentBrief",
    "TrendSource",
    "ViralContentResearcher",
    "ContentCurator",
]
