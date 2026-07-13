"""Channel 2: Company discovery → extract people by role.

Finds target companies, then identifies people at those companies for specific roles.
"""

from __future__ import annotations

import json
import subprocess

import httpx

from enrichment.research import _extract_json
from models import Candidate, CompanyProfile, IdentityKeys

COMPANY_DISCOVERY_PROMPT = """\
IMPORTANT: Use the WebSearch tool to find REAL companies. Do NOT fabricate names.

Search terms to guide your research: {query}

Find 15-20 companies that sell enterprise AI, industrial technology, supply chain \
platforms, or governance/compliance solutions — especially those active in the \
Middle East (UAE, Saudi Arabia, Qatar), Africa, India, or Southeast Asia.

Include a mix of:
- Companies selling AI platforms to large industrial enterprises or conglomerates \
(e.g. Palantir, C3.ai, o9 Solutions, Kinaxis, Blue Yonder, Databricks)
- Supply chain visibility and compliance platforms \
(e.g. Altana AI, Resilinc, FourKites, project44, Everstream, Sourcemap)
- Industrial software companies with MENA presence \
(e.g. AspenTech, Honeywell, Siemens, ABB, Rockwell)
- Gulf-based system integrators and sovereign AI companies \
(e.g. G42, Core42, Tonomus, Injazat, Elm, STC Solutions)
- AI governance and responsible AI companies \
(e.g. Holistic AI, Credo AI, Arthur AI, Robust Intelligence)
- Emerging startups in agentic AI, formal verification, or supply chain tech

For each company, note which region(s) they operate in.

Return ONLY a JSON array (no markdown fences, no prose):
[
  {{
    "name": "Company Name",
    "website": "https://...",
    "github_org": "org-name or null",
    "description": "What they do in 1-2 sentences",
    "relevance": "Why they're a good target for poaching talent",
    "region": "Gulf/Africa/India/Europe/US/Global"
  }}
]
"""

ENGINEER_DISCOVERY_PROMPT = """\
IMPORTANT: Use the WebSearch tool to find REAL people. Do NOT fabricate names. \
Only include people you can verify exist via web search results.

Find engineers and researchers who work at {company_name} ({website}).

Focus on people in these roles:
- AI/ML engineers
- Supply chain technology roles
- Formal verification / Lean / proof engineers
- AI governance / responsible AI roles
- Backend / infrastructure engineers
- Research scientists

Search their website team page, LinkedIn, GitHub org, conference talks, and blog posts.

Return ONLY a JSON array (no markdown fences, no prose):
[
  {{
    "name": "Full Name",
    "github_handle": "handle or null",
    "role": "Their role at the company",
    "evidence_url": "Where you found this info"
  }}
]
"""

ROLE_DISCOVERY_PROMPT = """\
IMPORTANT: Use the WebSearch tool to find REAL people. Do NOT fabricate names. \
Only include people you can verify exist via web search results.

Find people at {company_name} ({website}) who work in {role_type} roles.

{role_guidance}

Search their website team/leadership page, LinkedIn company page, press releases, \
conference speaker lists, and news articles.

Return ONLY a JSON array (no markdown fences, no prose):
[
  {{
    "name": "Full Name",
    "linkedin_url": "https://linkedin.com/in/... or null",
    "github_handle": "handle or null",
    "email": null,
    "current_role": "Their title at the company",
    "company": "{company_name}",
    "why_interesting": "Why this person is relevant",
    "evidence_url": "Where you found this info",
    "source_type": "linkedin/team_page/press_release/conference"
  }}
]
"""

ROLE_GUIDANCE = {
    "sales": "Look for: VP Sales, Regional Sales Director, Enterprise Account Executive, "
             "Head of Sales MENA/MEA/APAC. People who sell to large enterprises or government.",
    "marketing": "Look for: CMO, VP Marketing, Head of Content, Director of Communications. "
                 "People who market complex technology to enterprise buyers.",
    "partnerships": "Look for: VP Partnerships, Head of Alliances, Channel Director, "
                    "BD Director. People who build channel and technology partnerships.",
    "customer_success": "Look for: VP Customer Success, Head of Account Management, "
                        "Customer Success Director, Implementation Lead. People who manage "
                        "enterprise deployments and key accounts.",
    "customer_relations": "Look for: VP Customer Success, Head of Account Management, "
                          "Customer Success Director. People who manage enterprise accounts.",
    "domain_expert": "Look for: Chief Supply Chain Officer, VP Supply Chain, Head of Logistics, "
                     "Supply Chain Director. People with deep operational domain knowledge.",
    "product": "Look for: CPO, VP Product, Head of Product, Product Director. "
               "People who define enterprise AI or supply chain product strategy.",
}


def _get_github_token() -> str | None:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _claude_prompt(prompt: str, timeout: int = 600) -> str | None:
    """Run a prompt through claude -p, return raw stdout."""
    try:
        result = subprocess.run(
            [
                "claude", "-p", prompt,
                "--output-format", "text",
                "--allowedTools", "WebSearch,WebFetch",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout
        print(f"  claude -p failed (exit {result.returncode}): {result.stderr[:200]}")
    except FileNotFoundError:
        print("  ERROR: 'claude' CLI not found")
    except subprocess.TimeoutExpired:
        print(f"  ERROR: claude -p timed out after {timeout}s")
    return None


def _extract_json_array(text: str) -> list[dict] | None:
    """Extract a JSON array from claude output.

    Handles: bare JSON, fenced code blocks, JSON embedded in prose,
    and trailing commas / comments that break strict parsing.
    """
    import re

    text = text.strip()

    def _try_parse(s: str) -> list[dict] | None:
        try:
            result = json.loads(s)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        # Try fixing trailing commas (common Claude quirk)
        cleaned = re.sub(r",\s*([}\]])", r"\1", s)
        try:
            result = json.loads(cleaned)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        return None

    # Direct parse
    if text.startswith("["):
        r = _try_parse(text)
        if r is not None:
            return r

    # Fenced code block
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fenced:
        r = _try_parse(fenced.group(1))
        if r is not None:
            return r

    # Find the largest [...] in the text
    matches = list(re.finditer(r"\[", text))
    for m in matches:
        start = m.start()
        # Find matching close bracket
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    r = _try_parse(candidate)
                    if r is not None:
                        return r
                    break

    print(f"  DEBUG: Could not parse JSON from output ({len(text)} chars):")
    print(f"  DEBUG: First 300 chars: {text[:300]}")
    return None


def discover_companies(query: str) -> list[CompanyProfile]:
    """Use claude -p to find target companies for headhunting."""
    print("  Discovering target companies...")
    prompt = COMPANY_DISCOVERY_PROMPT.format(query=query)
    output = _claude_prompt(prompt)
    if not output:
        print("  ERROR: Company discovery failed")
        return []

    data = _extract_json_array(output)
    if not data:
        print("  WARNING: Could not parse company list")
        return []

    companies = []
    for item in data:
        companies.append(
            CompanyProfile(
                name=item.get("name", "?"),
                website=item.get("website", ""),
                github_org=item.get("github_org"),
                description=item.get("description", ""),
                relevance=item.get("relevance", ""),
                region=item.get("region", ""),
            )
        )
    print(f"  Found {len(companies)} companies")
    return companies


async def _fetch_org_members(org: str) -> list[dict]:
    """Fetch public members of a GitHub org via the REST API."""
    token = _get_github_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(
                f"https://api.github.com/orgs/{org}/members",
                headers=headers,
                params={"per_page": 100},
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
    return []


def find_engineers(company: CompanyProfile) -> list[Candidate]:
    """Find engineers at a company via GitHub org API + claude -p."""
    candidates: list[Candidate] = []

    # Stage B1: GitHub org members (if known)
    if company.github_org:
        import asyncio

        print(f"  Fetching GitHub org: {company.github_org}")
        members = asyncio.run(_fetch_org_members(company.github_org))
        for member in members:
            login = member.get("login", "")
            if login:
                candidates.append(
                    Candidate(
                        keys=IdentityKeys(github_handle=login),
                        source_channel=f"company/{company.name}",
                        source_url=f"https://github.com/{company.github_org}",
                        raw_context={
                            "company": company.name,
                            "source": "github_org",
                        },
                    )
                )
        if candidates:
            print(f"    Found {len(candidates)} org members")

    # Stage B2: Claude research for team members
    print(f"  Researching engineers at {company.name}...")
    prompt = ENGINEER_DISCOVERY_PROMPT.format(
        company_name=company.name, website=company.website
    )
    output = _claude_prompt(prompt)
    if output:
        data = _extract_json_array(output)
        if data:
            for person in data:
                candidates.append(
                    Candidate(
                        keys=IdentityKeys(
                            name=person.get("name"),
                            github_handle=person.get("github_handle"),
                        ),
                        source_channel=f"company/{company.name}",
                        source_url=person.get("evidence_url", company.website),
                        raw_context={
                            "company": company.name,
                            "role": person.get("role", ""),
                            "source": "claude_research",
                        },
                    )
                )
            print(f"    Found {len(data)} engineers via research")

    return candidates


def find_people_by_role(
    company: CompanyProfile, role_type: str
) -> list[Candidate]:
    """Find people at a company for a specific role type via claude -p."""
    guidance = ROLE_GUIDANCE.get(role_type, f"Look for people in {role_type} roles.")
    prompt = ROLE_DISCOVERY_PROMPT.format(
        company_name=company.name,
        website=company.website,
        role_type=role_type,
        role_guidance=guidance,
    )

    print(f"  Finding {role_type} people at {company.name}...")
    output = _claude_prompt(prompt)
    if not output:
        return []

    data = _extract_json_array(output)
    if not data:
        return []

    candidates = []
    for person in data:
        candidates.append(
            Candidate(
                keys=IdentityKeys(
                    name=person.get("name"),
                    github_handle=person.get("github_handle"),
                    email=person.get("email"),
                    linkedin_url=person.get("linkedin_url"),
                ),
                source_channel=f"company/{company.name}",
                source_url=person.get("evidence_url", company.website),
                raw_context={
                    "company": company.name,
                    "role": person.get("current_role", ""),
                    "signal": person.get("why_interesting", ""),
                    "source": "company_role_search",
                },
            )
        )
    print(f"    Found {len(candidates)} {role_type} candidates")
    return candidates


def search(query: str, limit: int = 10) -> list[Candidate]:
    """Full company channel: discover companies → extract engineers."""
    companies = discover_companies(query)
    all_candidates: list[Candidate] = []

    for company in companies[:limit]:
        engineers = find_engineers(company)
        all_candidates.extend(engineers)

    print(f"  Total: {len(all_candidates)} candidates from {len(companies)} companies")
    return all_candidates
