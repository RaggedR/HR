"""Channel 3: Direct person lookup.

Takes identity keys directly and goes straight to enrichment.
"""

from __future__ import annotations

from models import Candidate, IdentityKeys


def lookup(
    name: str | None = None,
    github: str | None = None,
    email: str | None = None,
    scholar_id: str | None = None,
    linkedin: str | None = None,
) -> Candidate:
    """Create a candidate from directly provided identity keys."""
    keys = IdentityKeys(
        name=name,
        github_handle=github,
        email=email,
        scholar_id=scholar_id,
        linkedin_url=linkedin,
    )
    source = f"https://github.com/{github}" if github else "direct lookup"
    return Candidate(
        keys=keys,
        source_channel="direct",
        source_url=source,
        raw_context={"source": "direct_input"},
    )
