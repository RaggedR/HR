"""Channel 1: Contrarian search across GitHub and Semantic Scholar.

Finds rising repos/papers and extracts their authors as candidates.
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx

# Import the contrarian search engine
sys.path.insert(0, os.path.expanduser("~/git/search"))
from domains import get_domain  # noqa: E402
from domains.base import Item  # noqa: E402

from models import Candidate, IdentityKeys  # noqa: E402

SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"


def _github_item_to_candidate(item: Item) -> Candidate:
    """Extract a candidate from a GitHub search result."""
    return Candidate(
        keys=IdentityKeys(
            name=None,  # GitHub login != real name; enrichment resolves this
            github_handle=item.author,
        ),
        source_channel="contrarian/github",
        source_url=item.url,
        breakout_score=item.breakout_score,
        raw_context={
            "repo": item.title,
            "description": item.metadata.get("description", ""),
            "language": item.metadata.get("language", ""),
            "stars": item.popularity,
            "recent_stars_7d": item.metadata.get("recent_stars_7d"),
        },
    )


async def _scholar_search_with_authors(
    query: str, max_popularity: int, days: int, limit: int
) -> list[Candidate]:
    """Run Scholar search and extract individual authors as candidates.

    We call the Semantic Scholar API directly (rather than through the
    search engine) because we need the raw author objects with authorId,
    which the search engine's Item flattens into a display string.
    """
    fields = (
        "title,url,authors,citationCount,influentialCitationCount,"
        "year,externalIds"
    )
    params = {"query": query, "limit": min(limit * 3, 100), "fields": fields}

    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(5):
            resp = await client.get(f"{SCHOLAR_API}/paper/search", params=params)
            if resp.status_code == 429:
                delay = 5 * (2 ** attempt)  # 5, 10, 20, 40, 80
                print(f"  Scholar rate limited, retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue
            resp.raise_for_status()
            break
        else:
            print("  Scholar rate limited after 5 attempts. Skipping.")
            return []

        data = resp.json()

    # Collect unique authors across all papers
    seen_authors: dict[str, Candidate] = {}  # keyed by authorId or name

    for paper in data.get("data", []):
        citations = paper.get("citationCount", 0) or 0
        if citations > max_popularity:
            continue

        influential = paper.get("influentialCitationCount", 0) or 0
        year = paper.get("year") or 2025
        age_days = max((2026 - year) * 365 + 180, 1)
        velocity = influential * 5 + citations * 0.5

        import math

        if citations > 0:
            score = velocity / (math.log(citations + 1) * age_days)
        else:
            score = velocity / age_days

        paper_url = paper.get("url", "")

        for author in paper.get("authors", []):
            author_name = author.get("name", "")
            author_id = author.get("authorId")
            key = author_id or author_name

            if not key:
                continue

            if key in seen_authors:
                # Accumulate: keep highest score, merge sources
                existing = seen_authors[key]
                if score > existing.breakout_score:
                    existing.breakout_score = score
                    existing.source_url = paper_url
                existing.raw_context.setdefault("papers", []).append(
                    paper.get("title", "")
                )
            else:
                seen_authors[key] = Candidate(
                    keys=IdentityKeys(
                        name=author_name or None,
                        scholar_id=author_id,
                    ),
                    source_channel="contrarian/scholar",
                    source_url=paper_url,
                    breakout_score=score,
                    raw_context={
                        "papers": [paper.get("title", "")],
                        "citations": citations,
                        "influential_citations": influential,
                    },
                )

    candidates = sorted(
        seen_authors.values(), key=lambda c: c.breakout_score, reverse=True
    )
    return candidates[:limit]


async def search_github(
    query: str, max_popularity: int = 500, days: int = 60, limit: int = 20
) -> list[Candidate]:
    """Run contrarian search on GitHub and extract repo owners."""
    domain = get_domain("github")
    items = await domain.search(query, max_popularity, days, limit)
    return [_github_item_to_candidate(item) for item in items]


async def search_scholar(
    query: str, max_popularity: int = 500, days: int = 60, limit: int = 20
) -> list[Candidate]:
    """Run contrarian search on Scholar and extract paper authors."""
    return await _scholar_search_with_authors(query, max_popularity, days, limit)


async def search_all(
    query: str, max_popularity: int = 500, days: int = 60, limit: int = 20
) -> list[Candidate]:
    """Run both GitHub and Scholar in parallel, return combined candidates."""
    github_results, scholar_results = await asyncio.gather(
        search_github(query, max_popularity, days, limit),
        search_scholar(query, max_popularity, days, limit),
    )
    return github_results + scholar_results
