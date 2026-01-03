"""
CLI interface for the Viral Content Researcher
"""

import asyncio
import click
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.tree import Tree
from rich import box

from viral_content_researcher.models import TrendSource, ContentCategory
from viral_content_researcher.researcher import ViralContentResearcher
from viral_content_researcher.curator import ContentCurator
from viral_content_researcher.storage import Storage
from viral_content_researcher.brief_generator import BriefGenerator


console = Console()


def run_async(coro):
    """Run an async function in the event loop"""
    return asyncio.get_event_loop().run_until_complete(coro)


def get_score_color(score: float) -> str:
    """Get color based on virality score"""
    if score >= 80:
        return "bright_green"
    elif score >= 60:
        return "green"
    elif score >= 40:
        return "yellow"
    elif score >= 20:
        return "orange1"
    else:
        return "red"


def get_urgency_color(urgency: str) -> str:
    """Get color based on urgency level"""
    colors = {
        "trending_now": "bright_red",
        "high": "red",
        "medium": "yellow",
        "low": "dim",
    }
    return colors.get(urgency, "white")


@click.group()
@click.version_option(version="1.0.0")
def main():
    """
    Viral Content Researcher - Find trending marketing topics

    Research and curate viral content opportunities for your marketing strategy.
    """
    pass


@main.command()
@click.option("--limit", "-l", default=15, help="Number of topics to show")
@click.option("--category", "-c", type=click.Choice([c.value for c in ContentCategory]), help="Filter by category")
@click.option("--source", "-s", type=click.Choice([s.value for s in TrendSource]), help="Filter by source")
@click.option("--min-score", default=30.0, help="Minimum virality score")
@click.option("--save", is_flag=True, help="Save results to database")
def trending(limit: int, category: Optional[str], source: Optional[str], min_score: float, save: bool):
    """Discover trending marketing topics from all sources"""

    async def _run():
        sources = [TrendSource(source)] if source else None
        categories = [ContentCategory(category)] if category else None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Researching trending topics...", total=None)

            async with ViralContentResearcher() as researcher:
                topics = await researcher.research_trending(
                    limit=limit,
                    categories=categories,
                    sources=sources,
                    min_score=min_score,
                )

        if not topics:
            console.print("[yellow]No trending topics found matching your criteria.[/yellow]")
            return

        # Create table
        table = Table(
            title="Trending Marketing Topics",
            box=box.ROUNDED,
            show_lines=True,
            title_style="bold magenta",
        )

        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="bold", max_width=50)
        table.add_column("Score", justify="center", width=8)
        table.add_column("Source", justify="center", width=12)
        table.add_column("Category", justify="center", width=15)
        table.add_column("Engagement", justify="right", width=12)

        for idx, topic in enumerate(topics, 1):
            score_color = get_score_color(topic.virality_score)
            engagement = f"{topic.score} / {topic.comments}c"

            table.add_row(
                str(idx),
                topic.title[:50] + "..." if len(topic.title) > 50 else topic.title,
                f"[{score_color}]{topic.virality_score:.0f}[/{score_color}]",
                topic.source.value,
                topic.category.value,
                engagement,
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(topics)} trending topics[/dim]")

        if save:
            async with Storage() as storage:
                saved = await storage.save_topics(topics)
                console.print(f"[green]Saved {saved} topics to database[/green]")

    run_async(_run())


@main.command()
@click.argument("query")
@click.option("--limit", "-l", default=15, help="Number of results")
@click.option("--source", "-s", type=click.Choice([s.value for s in TrendSource]), help="Search specific source")
def search(query: str, limit: int, source: Optional[str]):
    """Search for specific marketing topics"""

    async def _run():
        sources = [TrendSource(source)] if source else None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(f"Searching for '{query}'...", total=None)

            async with ViralContentResearcher() as researcher:
                topics = await researcher.search(query, limit=limit, sources=sources)

        if not topics:
            console.print(f"[yellow]No results found for '{query}'[/yellow]")
            return

        table = Table(
            title=f"Search Results: '{query}'",
            box=box.ROUNDED,
            show_lines=True,
        )

        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="bold", max_width=55)
        table.add_column("Score", justify="center", width=8)
        table.add_column("Source", justify="center", width=12)

        for idx, topic in enumerate(topics, 1):
            score_color = get_score_color(topic.virality_score)
            table.add_row(
                str(idx),
                topic.title[:55] + "..." if len(topic.title) > 55 else topic.title,
                f"[{score_color}]{topic.virality_score:.0f}[/{score_color}]",
                topic.source.value,
            )

        console.print(table)

    run_async(_run())


@main.command()
@click.option("--limit", "-l", default=5, help="Number of briefs to generate")
@click.option("--category", "-c", type=click.Choice([c.value for c in ContentCategory]), help="Filter by category")
@click.option("--save", is_flag=True, help="Save briefs to database")
def briefs(limit: int, category: Optional[str], save: bool):
    """Generate content briefs from trending topics"""

    async def _run():
        categories = [ContentCategory(category)] if category else None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Generating content briefs...", total=None)

            async with ViralContentResearcher() as researcher:
                topics = await researcher.research_trending(
                    limit=limit * 2,
                    categories=categories,
                    min_score=40.0,
                )

            generator = BriefGenerator()
            content_briefs = generator.generate_briefs_from_topics(topics, limit=limit)

        if not content_briefs:
            console.print("[yellow]No suitable topics found for brief generation.[/yellow]")
            return

        for idx, brief in enumerate(content_briefs, 1):
            urgency_color = get_urgency_color(brief.urgency)

            panel = Panel(
                f"""[bold]Hook:[/bold] {brief.hook}

[bold]Format:[/bold] {brief.suggested_format}  |  [bold]Words:[/bold] ~{brief.estimated_word_count}  |  [bold]Urgency:[/bold] [{urgency_color}]{brief.urgency}[/{urgency_color}]

[bold]Keywords:[/bold] {', '.join(brief.target_keywords[:5])}

[bold]Title Options:[/bold]
{chr(10).join('  - ' + t for t in brief.suggested_title_variants[:3])}
""",
                title=f"[bold cyan]Brief #{idx}: {brief.title}[/bold cyan]",
                border_style="cyan",
            )
            console.print(panel)

        if save:
            async with Storage() as storage:
                for brief in content_briefs:
                    await storage.save_brief(brief)
                console.print(f"[green]Saved {len(content_briefs)} briefs to database[/green]")

    run_async(_run())


@main.command()
@click.option("--days", "-d", default=7, help="Number of days to plan")
@click.option("--category", "-c", type=click.Choice([c.value for c in ContentCategory]), help="Filter by category")
def calendar(days: int, category: Optional[str]):
    """Generate a content calendar from trending topics"""

    async def _run():
        categories = [ContentCategory(category)] if category else None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Building content calendar...", total=None)

            async with ViralContentResearcher() as researcher:
                topics = await researcher.research_trending(
                    limit=days * 2,
                    categories=categories,
                    min_score=35.0,
                )

            generator = BriefGenerator()
            cal = generator.generate_content_calendar(topics, days=days)

        if not cal:
            console.print("[yellow]Could not generate calendar. Not enough topics found.[/yellow]")
            return

        table = Table(
            title="Content Calendar",
            box=box.ROUNDED,
            show_lines=True,
            title_style="bold magenta",
        )

        table.add_column("Date", style="cyan", width=12)
        table.add_column("Day", width=10)
        table.add_column("Topic", style="bold", max_width=40)
        table.add_column("Format", justify="center", width=12)
        table.add_column("Urgency", justify="center", width=12)
        table.add_column("Est. Time", justify="right", width=10)

        for entry in cal:
            urgency_color = get_urgency_color(entry["urgency"])
            table.add_row(
                entry["date"],
                entry["day_of_week"][:3],
                entry["topic"][:40] + "..." if len(entry["topic"]) > 40 else entry["topic"],
                entry["format"],
                f"[{urgency_color}]{entry['urgency']}[/{urgency_color}]",
                entry["estimated_time"],
            )

        console.print(table)

    run_async(_run())


@main.command()
def insights():
    """Get marketing insights and recommendations"""

    async def _run():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Analyzing marketing trends...", total=None)

            async with ViralContentResearcher() as researcher:
                data = await researcher.get_marketing_insights(limit=10)

        # Trending Keywords
        console.print("\n[bold magenta]Trending Keywords[/bold magenta]")
        keywords_str = ", ".join([f"[cyan]{kw}[/cyan] ({count})" for kw, count in data["trending_keywords"][:10]])
        console.print(keywords_str)

        # Category Breakdown
        console.print("\n[bold magenta]Topics by Category[/bold magenta]")
        tree = Tree("[bold]Categories[/bold]")
        for cat, count in sorted(data["category_breakdown"].items(), key=lambda x: x[1], reverse=True):
            tree.add(f"{cat}: {count} topics")
        console.print(tree)

        # Top Recommendations
        console.print("\n[bold magenta]Content Recommendations[/bold magenta]")
        for idx, rec in enumerate(data["recommendations"], 1):
            urgency_color = get_urgency_color(rec["urgency"])
            console.print(f"\n[bold]{idx}. {rec['topic']}[/bold]")
            console.print(f"   Format: {rec['format']} | Urgency: [{urgency_color}]{rec['urgency']}[/{urgency_color}]")
            console.print("   Angles:")
            for angle in rec["angles"]:
                console.print(f"     - {angle}")

    run_async(_run())


@main.command()
@click.option("--limit", "-l", default=25, help="Number of saved topics to show")
@click.option("--category", "-c", type=click.Choice([c.value for c in ContentCategory]), help="Filter by category")
def saved(limit: int, category: Optional[str]):
    """View saved topics from the database"""

    async def _run():
        cat = ContentCategory(category) if category else None

        async with Storage() as storage:
            topics = await storage.get_topics(
                limit=limit,
                saved_only=True,
                category=cat,
            )

        if not topics:
            console.print("[yellow]No saved topics found.[/yellow]")
            console.print("[dim]Use --save flag with 'trending' or 'search' to save topics.[/dim]")
            return

        table = Table(title="Saved Topics", box=box.ROUNDED)

        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="bold", max_width=50)
        table.add_column("Score", justify="center", width=8)
        table.add_column("Category", justify="center", width=15)

        for idx, topic in enumerate(topics, 1):
            score_color = get_score_color(topic.virality_score)
            table.add_row(
                str(idx),
                topic.title[:50],
                f"[{score_color}]{topic.virality_score:.0f}[/{score_color}]",
                topic.category.value,
            )

        console.print(table)

    run_async(_run())


@main.command()
def stats():
    """Show database statistics"""

    async def _run():
        async with Storage() as storage:
            data = await storage.get_stats()

        console.print("\n[bold magenta]Database Statistics[/bold magenta]\n")

        console.print(f"Total Topics: [cyan]{data['total_topics']}[/cyan]")
        console.print(f"Saved Topics: [green]{data['saved_topics']}[/green]")
        console.print(f"Content Briefs: [cyan]{data['total_briefs']}[/cyan]")

        if data.get("topics_by_source"):
            console.print("\n[bold]Topics by Source:[/bold]")
            for source, count in data["topics_by_source"].items():
                console.print(f"  {source}: {count}")

        if data.get("topics_by_category"):
            console.print("\n[bold]Topics by Category:[/bold]")
            for cat, count in sorted(data["topics_by_category"].items(), key=lambda x: x[1], reverse=True)[:5]:
                console.print(f"  {cat}: {count}")

    run_async(_run())


@main.command()
@click.option("--days", "-d", default=30, help="Remove topics older than this many days")
@click.confirmation_option(prompt="This will delete old topics. Continue?")
def cleanup(days: int):
    """Clean up old topics from database"""

    async def _run():
        async with Storage() as storage:
            deleted = await storage.cleanup_old_topics(days=days)

        console.print(f"[green]Cleaned up {deleted} old topics.[/green]")

    run_async(_run())


@main.command()
@click.argument("topic_index", type=int)
@click.option("--format", "-f", "format_type", type=click.Choice(["blog_post", "guide", "listicle", "tutorial", "comparison", "case_study"]), help="Content format")
def brief(topic_index: int, format_type: Optional[str]):
    """Generate a detailed brief for a specific topic (by index from last search)"""

    async def _run():
        # Get recent topics
        async with Storage() as storage:
            topics = await storage.get_topics(limit=25, min_score=0)

        if topic_index < 1 or topic_index > len(topics):
            console.print(f"[red]Invalid topic index. Choose 1-{len(topics)}[/red]")
            return

        topic = topics[topic_index - 1]
        generator = BriefGenerator()
        content_brief = generator.generate_brief(topic, format_type=format_type)

        # Display as markdown
        md = generator.format_brief_as_markdown(content_brief)
        console.print(Markdown(md))

    run_async(_run())


@main.command("sources")
def list_sources():
    """List available data sources"""
    console.print("\n[bold magenta]Available Data Sources[/bold magenta]\n")

    sources_info = [
        ("reddit", "Marketing subreddits (r/marketing, r/SEO, r/socialmedia, etc.)", True),
        ("hacker_news", "Tech & startup news from Hacker News", True),
        ("rss_feed", "Marketing blogs (HubSpot, Moz, Neil Patel, etc.)", True),
        ("product_hunt", "New marketing tools and products", True),
        ("google_trends", "Google Trends data (requires pytrends)", True),
        ("twitter", "Twitter/X trending topics (requires API key)", False),
        ("linkedin", "LinkedIn trending content (coming soon)", False),
    ]

    table = Table(box=box.ROUNDED)
    table.add_column("Source", style="cyan")
    table.add_column("Description")
    table.add_column("Status", justify="center")

    for source, desc, available in sources_info:
        status = "[green]Available[/green]" if available else "[dim]Unavailable[/dim]"
        table.add_row(source, desc, status)

    console.print(table)


@main.command("categories")
def list_categories():
    """List content categories"""
    console.print("\n[bold magenta]Content Categories[/bold magenta]\n")

    for cat in ContentCategory:
        console.print(f"  [cyan]{cat.value}[/cyan]")


if __name__ == "__main__":
    main()
