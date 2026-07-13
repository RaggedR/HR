"""Data models for the HR headhunting tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class IdentityKeys:
    """Deduplication anchor. Any shared non-null key = same person."""

    name: str | None = None
    github_handle: str | None = None
    email: str | None = None
    scholar_id: str | None = None
    linkedin_url: str | None = None

    def strongest_key(self) -> str:
        """Return the most specific identifier we have."""
        if self.github_handle:
            return f"github:{self.github_handle}"
        if self.email:
            return f"email:{self.email}"
        if self.scholar_id:
            return f"scholar:{self.scholar_id}"
        if self.name:
            return f"name:{self.name}"
        return "unknown"

    def slug(self) -> str:
        """Filesystem-safe identifier for this candidate."""
        if self.github_handle:
            return self.github_handle.lower()
        if self.name:
            return self.name.lower().replace(" ", "-").replace(".", "")
        return "unknown"


@dataclass
class Candidate:
    """Raw candidate before enrichment. Produced by channels."""

    keys: IdentityKeys
    source_channel: str  # "contrarian", "company", "direct"
    source_url: str
    breakout_score: float = 0.0
    raw_context: dict = field(default_factory=dict)


@dataclass
class Profile:
    """Enriched profile from claude -p research."""

    name: str | None = None
    confidence: float = 0.0
    location: str | None = None
    roles: list[str] = field(default_factory=list)
    links: dict[str, str] = field(default_factory=dict)
    summary: str = ""
    gaps: list[str] = field(default_factory=list)
    next_key_needed: str | None = None


@dataclass
class Verification:
    """Adversarial refute pass output."""

    confirmed: bool = False
    confidence_cap: float = 1.0
    refute_notes: str = ""


@dataclass
class Dossier:
    """Final enriched output for one candidate."""

    keys: IdentityKeys
    profile: Profile
    verification: Verification
    sources: list[str] = field(default_factory=list)
    source_channels: list[str] = field(default_factory=list)
    highest_breakout_score: float = 0.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    rank_score: float = 0.0

    def compute_rank(self) -> None:
        import math

        self.rank_score = self.profile.confidence * (
            1 + math.log(self.highest_breakout_score + 1)
        )


@dataclass
class CompanyProfile:
    """Target company for headhunting. Persisted to data/companies.json."""

    name: str
    website: str
    github_org: str | None = None
    description: str = ""
    relevance: str = ""
    region: str = ""  # Gulf, Africa, India, Europe, etc.
    added_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def slug(self) -> str:
        return self.name.lower().replace(" ", "-").replace(".", "")
