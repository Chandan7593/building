"""
SQLite storage layer for persisting research data
"""

import json
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

from viral_content_researcher.models import (
    Topic,
    ContentBrief,
    TrendSource,
    ContentCategory,
    ResearchSession,
)


class Storage:
    """
    Async SQLite storage for topics, briefs, and research sessions.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize storage.

        Args:
            db_path: Path to SQLite database (defaults to ~/.vcr/data.db)
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path.home() / ".vcr" / "data.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to the database and initialize tables"""
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._init_tables()

    async def close(self):
        """Close the database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _init_tables(self):
        """Initialize database tables"""
        await self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                virality_score REAL DEFAULT 0,
                trending_velocity REAL DEFAULT 0,
                keywords TEXT,
                hashtags TEXT,
                author TEXT,
                published_at TEXT,
                discovered_at TEXT NOT NULL,
                content_angle TEXT,
                target_audience TEXT,
                saved INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS content_briefs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                hook TEXT NOT NULL,
                outline TEXT NOT NULL,
                source_topic_ids TEXT,
                suggested_format TEXT DEFAULT 'blog_post',
                estimated_word_count INTEGER DEFAULT 1500,
                target_keywords TEXT,
                meta_description TEXT,
                suggested_title_variants TEXT,
                category TEXT NOT NULL,
                urgency TEXT DEFAULT 'medium',
                notes TEXT,
                competitors TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS research_sessions (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                topics_discovered INTEGER DEFAULT 0,
                topics_curated INTEGER DEFAULT 0,
                briefs_generated INTEGER DEFAULT 0,
                sources_queried TEXT,
                filters_applied TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_topics_source ON topics(source);
            CREATE INDEX IF NOT EXISTS idx_topics_category ON topics(category);
            CREATE INDEX IF NOT EXISTS idx_topics_virality ON topics(virality_score DESC);
            CREATE INDEX IF NOT EXISTS idx_topics_discovered ON topics(discovered_at DESC);
            CREATE INDEX IF NOT EXISTS idx_topics_saved ON topics(saved);
            CREATE INDEX IF NOT EXISTS idx_briefs_category ON content_briefs(category);
            CREATE INDEX IF NOT EXISTS idx_briefs_created ON content_briefs(created_at DESC);
        """)
        await self._connection.commit()

    def _topic_to_row(self, topic: Topic) -> dict:
        """Convert Topic to database row"""
        return {
            "id": topic.id or str(uuid.uuid4()),
            "title": topic.title,
            "description": topic.description,
            "url": topic.url,
            "source": topic.source.value,
            "category": topic.category.value,
            "score": topic.score,
            "comments": topic.comments,
            "shares": topic.shares,
            "views": topic.views,
            "virality_score": topic.virality_score,
            "trending_velocity": topic.trending_velocity,
            "keywords": json.dumps(topic.keywords),
            "hashtags": json.dumps(topic.hashtags),
            "author": topic.author,
            "published_at": topic.published_at.isoformat() if topic.published_at else None,
            "discovered_at": topic.discovered_at.isoformat(),
            "content_angle": topic.content_angle,
            "target_audience": topic.target_audience,
        }

    def _row_to_topic(self, row: aiosqlite.Row) -> Topic:
        """Convert database row to Topic"""
        return Topic(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            url=row["url"],
            source=TrendSource(row["source"]),
            category=ContentCategory(row["category"]),
            score=row["score"],
            comments=row["comments"],
            shares=row["shares"],
            views=row["views"],
            virality_score=row["virality_score"],
            trending_velocity=row["trending_velocity"],
            keywords=json.loads(row["keywords"]) if row["keywords"] else [],
            hashtags=json.loads(row["hashtags"]) if row["hashtags"] else [],
            author=row["author"],
            published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
            discovered_at=datetime.fromisoformat(row["discovered_at"]),
            content_angle=row["content_angle"],
            target_audience=row["target_audience"],
        )

    async def save_topic(self, topic: Topic, saved: bool = False) -> str:
        """Save a topic to the database"""
        row = self._topic_to_row(topic)
        row["saved"] = 1 if saved else 0

        await self._connection.execute("""
            INSERT OR REPLACE INTO topics
            (id, title, description, url, source, category, score, comments,
             shares, views, virality_score, trending_velocity, keywords,
             hashtags, author, published_at, discovered_at, content_angle,
             target_audience, saved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["id"], row["title"], row["description"], row["url"],
            row["source"], row["category"], row["score"], row["comments"],
            row["shares"], row["views"], row["virality_score"],
            row["trending_velocity"], row["keywords"], row["hashtags"],
            row["author"], row["published_at"], row["discovered_at"],
            row["content_angle"], row["target_audience"], row["saved"],
        ))
        await self._connection.commit()
        return row["id"]

    async def save_topics(self, topics: list[Topic]) -> int:
        """Save multiple topics to the database"""
        count = 0
        for topic in topics:
            await self.save_topic(topic)
            count += 1
        return count

    async def get_topic(self, topic_id: str) -> Optional[Topic]:
        """Get a topic by ID"""
        async with self._connection.execute(
            "SELECT * FROM topics WHERE id = ?", (topic_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return self._row_to_topic(row) if row else None

    async def get_topics(
        self,
        limit: int = 25,
        offset: int = 0,
        source: Optional[TrendSource] = None,
        category: Optional[ContentCategory] = None,
        min_score: float = 0,
        saved_only: bool = False,
    ) -> list[Topic]:
        """Get topics with optional filters"""
        query = "SELECT * FROM topics WHERE virality_score >= ?"
        params = [min_score]

        if source:
            query += " AND source = ?"
            params.append(source.value)

        if category:
            query += " AND category = ?"
            params.append(category.value)

        if saved_only:
            query += " AND saved = 1"

        query += " ORDER BY virality_score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with self._connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_topic(row) for row in rows]

    async def search_topics(self, query: str, limit: int = 25) -> list[Topic]:
        """Search topics by title or description"""
        search_query = f"%{query}%"
        async with self._connection.execute("""
            SELECT * FROM topics
            WHERE title LIKE ? OR description LIKE ? OR keywords LIKE ?
            ORDER BY virality_score DESC
            LIMIT ?
        """, (search_query, search_query, search_query, limit)) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_topic(row) for row in rows]

    async def mark_saved(self, topic_id: str, saved: bool = True) -> bool:
        """Mark a topic as saved/unsaved"""
        result = await self._connection.execute(
            "UPDATE topics SET saved = ? WHERE id = ?",
            (1 if saved else 0, topic_id)
        )
        await self._connection.commit()
        return result.rowcount > 0

    async def save_brief(self, brief: ContentBrief) -> str:
        """Save a content brief to the database"""
        brief_id = brief.id or str(uuid.uuid4())

        await self._connection.execute("""
            INSERT OR REPLACE INTO content_briefs
            (id, title, hook, outline, source_topic_ids, suggested_format,
             estimated_word_count, target_keywords, meta_description,
             suggested_title_variants, category, urgency, notes, competitors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            brief_id, brief.title, brief.hook,
            json.dumps(brief.outline),
            json.dumps([t.id for t in brief.source_topics]),
            brief.suggested_format, brief.estimated_word_count,
            json.dumps(brief.target_keywords), brief.meta_description,
            json.dumps(brief.suggested_title_variants),
            brief.category.value, brief.urgency, brief.notes,
            json.dumps(brief.competitors),
        ))
        await self._connection.commit()
        return brief_id

    async def get_briefs(
        self,
        limit: int = 25,
        offset: int = 0,
        category: Optional[ContentCategory] = None,
    ) -> list[ContentBrief]:
        """Get content briefs with optional filters"""
        query = "SELECT * FROM content_briefs"
        params = []

        if category:
            query += " WHERE category = ?"
            params.append(category.value)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with self._connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            briefs = []
            for row in rows:
                brief = ContentBrief(
                    id=row["id"],
                    title=row["title"],
                    hook=row["hook"],
                    outline=json.loads(row["outline"]),
                    suggested_format=row["suggested_format"],
                    estimated_word_count=row["estimated_word_count"],
                    target_keywords=json.loads(row["target_keywords"]) if row["target_keywords"] else [],
                    meta_description=row["meta_description"],
                    suggested_title_variants=json.loads(row["suggested_title_variants"]) if row["suggested_title_variants"] else [],
                    category=ContentCategory(row["category"]),
                    urgency=row["urgency"],
                    notes=row["notes"],
                    competitors=json.loads(row["competitors"]) if row["competitors"] else [],
                )
                briefs.append(brief)
            return briefs

    async def get_stats(self) -> dict:
        """Get database statistics"""
        stats = {}

        async with self._connection.execute("SELECT COUNT(*) FROM topics") as cursor:
            row = await cursor.fetchone()
            stats["total_topics"] = row[0]

        async with self._connection.execute("SELECT COUNT(*) FROM topics WHERE saved = 1") as cursor:
            row = await cursor.fetchone()
            stats["saved_topics"] = row[0]

        async with self._connection.execute("SELECT COUNT(*) FROM content_briefs") as cursor:
            row = await cursor.fetchone()
            stats["total_briefs"] = row[0]

        async with self._connection.execute("""
            SELECT source, COUNT(*) as count FROM topics GROUP BY source
        """) as cursor:
            rows = await cursor.fetchall()
            stats["topics_by_source"] = {row["source"]: row["count"] for row in rows}

        async with self._connection.execute("""
            SELECT category, COUNT(*) as count FROM topics GROUP BY category
        """) as cursor:
            rows = await cursor.fetchall()
            stats["topics_by_category"] = {row["category"]: row["count"] for row in rows}

        return stats

    async def cleanup_old_topics(self, days: int = 30) -> int:
        """Remove topics older than specified days (keeps saved ones)"""
        result = await self._connection.execute("""
            DELETE FROM topics
            WHERE saved = 0
            AND datetime(discovered_at) < datetime('now', ?)
        """, (f"-{days} days",))
        await self._connection.commit()
        return result.rowcount

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
