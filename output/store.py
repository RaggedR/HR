"""Local JSON dossier store in data/."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from models import CompanyProfile, Dossier, IdentityKeys, Profile, Verification

DATA_DIR = Path(__file__).parent.parent / "data"


def save_dossier(dossier: Dossier) -> Path:
    """Save a dossier to data/<slug>.json. Returns the path."""
    DATA_DIR.mkdir(exist_ok=True)
    slug = dossier.keys.slug()
    path = DATA_DIR / f"{slug}.json"
    with open(path, "w") as f:
        json.dump(asdict(dossier), f, indent=2)
    return path


def load_dossier(slug: str) -> Dossier | None:
    """Load a dossier by slug. Returns None if not found."""
    path = DATA_DIR / f"{slug}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return _dict_to_dossier(data)


def list_dossiers() -> list[Dossier]:
    """Load all dossiers from data/."""
    if not DATA_DIR.exists():
        return []
    dossiers = []
    for path in sorted(DATA_DIR.glob("*.json")):
        if path.name == "companies.json":
            continue
        with open(path) as f:
            data = json.load(f)
        try:
            dossiers.append(_dict_to_dossier(data))
        except (KeyError, TypeError):
            continue
    return dossiers


def find_dossier_by_name(name: str) -> Dossier | None:
    """Search dossiers by name (case-insensitive substring)."""
    name_lower = name.lower()
    for d in list_dossiers():
        if d.keys.name and name_lower in d.keys.name.lower():
            return d
        if d.keys.github_handle and name_lower in d.keys.github_handle.lower():
            return d
    return None


COMPANIES_PATH = DATA_DIR / "companies.json"


def load_companies() -> list[CompanyProfile]:
    """Load the target company list from data/companies.json."""
    if not COMPANIES_PATH.exists():
        return []
    with open(COMPANIES_PATH) as f:
        data = json.load(f)
    return [CompanyProfile(**item) for item in data]


def save_companies(companies: list[CompanyProfile]) -> Path:
    """Save the target company list to data/companies.json."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(COMPANIES_PATH, "w") as f:
        json.dump([asdict(c) for c in companies], f, indent=2)
    return COMPANIES_PATH


def find_company_by_name(name: str) -> CompanyProfile | None:
    """Search companies by name (case-insensitive substring)."""
    name_lower = name.lower()
    for c in load_companies():
        if name_lower in c.name.lower():
            return c
    return None


def add_company(company: CompanyProfile) -> list[CompanyProfile]:
    """Add a company to the list, deduplicating by name. Returns updated list."""
    companies = load_companies()
    existing = [c for c in companies if c.name.lower() == company.name.lower()]
    if existing:
        # Update in place
        idx = companies.index(existing[0])
        companies[idx] = company
    else:
        companies.append(company)
    save_companies(companies)
    return companies


def remove_company(name: str) -> list[CompanyProfile]:
    """Remove a company by name. Returns updated list."""
    companies = load_companies()
    companies = [c for c in companies if name.lower() not in c.name.lower()]
    save_companies(companies)
    return companies


def _dict_to_dossier(data: dict) -> Dossier:
    return Dossier(
        keys=IdentityKeys(**data["keys"]),
        profile=Profile(**data["profile"]),
        verification=Verification(**data["verification"]),
        sources=data.get("sources", []),
        source_channels=data.get("source_channels", []),
        highest_breakout_score=data.get("highest_breakout_score", 0.0),
        created_at=data.get("created_at", ""),
        rank_score=data.get("rank_score", 0.0),
    )
