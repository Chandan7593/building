# Viral Content Researcher

A powerful CLI tool that finds and curates trending marketing topics to help you write viral content. Research trending discussions across Reddit, Hacker News, RSS feeds, Product Hunt, and Google Trends to discover content opportunities with high viral potential.

## Features

- **Multi-Source Research**: Aggregate trending topics from multiple platforms
  - Reddit (20+ marketing subreddits)
  - Hacker News (tech & startup insights)
  - RSS Feeds (major marketing blogs)
  - Product Hunt (new marketing tools)
  - Google Trends (search trends)

- **Smart Curation**: AI-powered scoring and filtering
  - Virality score based on engagement metrics
  - Recency-weighted algorithms
  - Category-based filtering
  - Duplicate detection

- **Content Brief Generation**: Actionable content plans
  - Auto-generated hooks and outlines
  - SEO keyword suggestions
  - Multiple title variants
  - Word count estimates

- **Content Calendar**: Plan your content schedule
  - 7-day content calendars
  - Urgency-based prioritization
  - Format recommendations

- **Local Storage**: SQLite database for persistence
  - Save favorite topics
  - Track research history
  - Export capabilities

## Installation

```bash
# Clone the repository
git clone https://github.com/example/viral-content-researcher.git
cd viral-content-researcher

# Install with pip
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

## Quick Start

```bash
# Discover trending marketing topics
vcr trending

# Search for specific topics
vcr search "AI marketing"

# Generate content briefs
vcr briefs --limit 5

# Create a content calendar
vcr calendar --days 7

# Get marketing insights
vcr insights
```

## Commands

### `vcr trending`
Discover trending marketing topics from all configured sources.

```bash
# Basic usage
vcr trending

# Limit results
vcr trending --limit 25

# Filter by category
vcr trending --category seo

# Filter by source
vcr trending --source reddit

# Set minimum virality score
vcr trending --min-score 50

# Save results to database
vcr trending --save
```

### `vcr search <query>`
Search for specific marketing topics across all sources.

```bash
vcr search "content marketing"
vcr search "tiktok strategy" --limit 20
vcr search "email automation" --source hacker_news
```

### `vcr briefs`
Generate actionable content briefs from top trending topics.

```bash
vcr briefs
vcr briefs --limit 10
vcr briefs --category ai_marketing
vcr briefs --save
```

### `vcr calendar`
Generate a content calendar based on trending topics.

```bash
vcr calendar
vcr calendar --days 14
vcr calendar --category social_media
```

### `vcr insights`
Get high-level marketing insights and recommendations.

```bash
vcr insights
```

### `vcr saved`
View saved topics from the database.

```bash
vcr saved
vcr saved --limit 50
vcr saved --category growth_hacking
```

### `vcr stats`
Show database statistics.

```bash
vcr stats
```

### `vcr sources`
List all available data sources.

```bash
vcr sources
```

### `vcr categories`
List all content categories.

```bash
vcr categories
```

### `vcr cleanup`
Remove old topics from the database.

```bash
vcr cleanup --days 30
```

## Content Categories

| Category | Description |
|----------|-------------|
| `seo` | Search engine optimization |
| `social_media` | Social media marketing |
| `email_marketing` | Email campaigns and newsletters |
| `content_marketing` | Blog posts, guides, content strategy |
| `paid_ads` | PPC, display ads, paid campaigns |
| `analytics` | Data, metrics, measurement |
| `branding` | Brand strategy and identity |
| `growth_hacking` | Viral growth, unconventional tactics |
| `influencer` | Influencer and creator marketing |
| `video_marketing` | YouTube, video content |
| `ai_marketing` | AI tools and automation |
| `ecommerce` | Online store marketing |
| `b2b` | Business-to-business marketing |
| `startup` | Startup marketing and launches |

## Data Sources

### Reddit
Monitors 20+ marketing-related subreddits including:
- r/marketing, r/digital_marketing
- r/SEO, r/bigseo
- r/socialmedia, r/content_marketing
- r/Entrepreneur, r/startups
- r/growthacking, r/ecommerce

### Hacker News
Fetches top stories and Show HN posts, filtering for marketing-relevant content about:
- Growth strategies
- Marketing tools
- Startup launches
- AI/automation

### RSS Feeds
Aggregates from major marketing blogs:
- HubSpot Marketing Blog
- Search Engine Land
- Search Engine Journal
- Moz Blog
- Content Marketing Institute
- Neil Patel
- Social Media Examiner
- And more...

### Product Hunt
Tracks new product launches in categories:
- Marketing tools
- SEO software
- Social media tools
- Analytics platforms
- AI/automation tools

### Google Trends
Fetches trending searches and related queries (requires `pytrends`).

## Programmatic Usage

```python
import asyncio
from viral_content_researcher import ViralContentResearcher, ContentCurator
from viral_content_researcher.brief_generator import BriefGenerator

async def main():
    # Research trending topics
    async with ViralContentResearcher() as researcher:
        topics = await researcher.research_trending(limit=10)

        for topic in topics:
            print(f"{topic.title} - Score: {topic.virality_score}")

    # Generate content briefs
    generator = BriefGenerator()
    briefs = generator.generate_briefs_from_topics(topics, limit=5)

    for brief in briefs:
        print(f"Brief: {brief.title}")
        print(f"Hook: {brief.hook}")
        print(f"Format: {brief.suggested_format}")

asyncio.run(main())
```

## Configuration

### Environment Variables

```bash
# Optional API keys for enhanced features
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_secret"
export NEWS_API_KEY="your_api_key"
```

### Custom RSS Feeds

```python
from viral_content_researcher.scrapers import RSSFeedScraper
from viral_content_researcher.models import ContentCategory

scraper = RSSFeedScraper()
scraper.add_feed(
    "https://example.com/feed",
    "Example Blog",
    ContentCategory.CONTENT_MARKETING
)
```

## Virality Score

Topics are scored from 0-100 based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Engagement | 25% | Upvotes, comments, shares |
| Recency | 20% | How recently published |
| Relevance | 25% | Marketing keyword density |
| Velocity | 15% | Growth rate of engagement |
| Uniqueness | 15% | Distinctiveness vs. other topics |

## Project Structure

```
viral-content-researcher/
├── src/
│   └── viral_content_researcher/
│       ├── __init__.py
│       ├── cli.py              # CLI interface
│       ├── models.py           # Data models
│       ├── researcher.py       # Main researcher class
│       ├── curator.py          # Curation & scoring
│       ├── storage.py          # SQLite storage
│       ├── brief_generator.py  # Content brief generation
│       └── scrapers/
│           ├── __init__.py
│           ├── base.py         # Base scraper class
│           ├── reddit.py       # Reddit scraper
│           ├── google_trends.py
│           ├── hacker_news.py
│           ├── rss_feeds.py
│           └── product_hunt.py
├── pyproject.toml
└── README.md
```

## Requirements

- Python 3.9+
- aiohttp
- beautifulsoup4
- click
- rich
- pydantic
- aiosqlite
- feedparser
- tenacity
- pytrends (optional, for Google Trends)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
