"""Candidate deduplication by identity key overlap."""

from __future__ import annotations

import re

from models import Candidate, IdentityKeys


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    return re.sub(r"\s+", " ", name)


def shares_key(a: IdentityKeys, b: IdentityKeys) -> bool:
    """True if any non-null identity key matches."""
    pairs = [
        (a.github_handle and a.github_handle.lower(),
         b.github_handle and b.github_handle.lower()),
        (a.email and a.email.lower(),
         b.email and b.email.lower()),
        (a.scholar_id, b.scholar_id),
        (a.linkedin_url and a.linkedin_url.lower(),
         b.linkedin_url and b.linkedin_url.lower()),
    ]
    for x, y in pairs:
        if x and y and x == y:
            return True

    # Name-only match: require exact normalized match (conservative)
    if a.name and b.name:
        if normalize_name(a.name) == normalize_name(b.name):
            return True

    return False


def _merge_keys(group: list[Candidate]) -> IdentityKeys:
    """Merge identity keys from a group, preferring non-null values."""
    merged = IdentityKeys()
    for c in group:
        merged.name = merged.name or c.keys.name
        merged.github_handle = merged.github_handle or c.keys.github_handle
        merged.email = merged.email or c.keys.email
        merged.scholar_id = merged.scholar_id or c.keys.scholar_id
        merged.linkedin_url = merged.linkedin_url or c.keys.linkedin_url
    return merged


def deduplicate(candidates: list[Candidate]) -> list[Candidate]:
    """Merge candidates sharing any identity key. Returns one per person."""
    groups: list[list[Candidate]] = []

    for candidate in candidates:
        merged_into = None
        for group in groups:
            if shares_key(candidate.keys, group[0].keys):
                group.append(candidate)
                merged_into = group
                break
        if merged_into is None:
            groups.append([candidate])

    results = []
    for group in groups:
        merged_keys = _merge_keys(group)
        best = max(group, key=lambda c: c.breakout_score)
        results.append(
            Candidate(
                keys=merged_keys,
                source_channel=", ".join(sorted({c.source_channel for c in group})),
                source_url=best.source_url,
                breakout_score=max(c.breakout_score for c in group),
                raw_context={
                    "merged_from": len(group),
                    "all_sources": [c.source_url for c in group],
                    "all_context": [c.raw_context for c in group],
                },
            )
        )
    return results
