"""WEB+FUSE enrichment: research a candidate via headless claude -p."""

from __future__ import annotations

import json
import re
import subprocess

from models import IdentityKeys, Profile


RESEARCH_PROMPT = """\
You are a professional researcher building a candidate profile for a hiring team.

## Known Identity Keys
{keys_json}

## Source Context
How we found this person: {source_channel}
Source URL: {source_url}
Additional context: {context_json}

## Task
Research this person using web search. Build a structured profile.

Rules:
- Only assert facts you can find evidence for. Do not speculate.
- Mark fields null if genuinely unknown — gaps are first-class information.
- If you find conflicting information, surface it in gaps[], don't resolve it silently.
- The "confidence" field is YOUR confidence that this profile describes one real \
person with correct identity (not a name collision, not a stale profile). Be conservative.
- Focus the summary on relevance to: AI governance, supply chain tech, formal \
verification, agentic engineering, Lean.

## Output
Return ONLY a JSON object (no markdown fences, no prose before/after):
{{
  "name": "Full name or null",
  "confidence": 0.0,
  "location": "City, Country or null",
  "roles": ["current role", "previous notable role"],
  "links": {{"github": "url", "linkedin": "url", "website": "url"}},
  "summary": "2-3 sentence synthesis",
  "gaps": ["what you couldn't confirm"],
  "next_key_needed": "the one piece of info that would most raise confidence"
}}
"""


def _build_keys_dict(keys: IdentityKeys) -> dict:
    d = {}
    if keys.name:
        d["name"] = keys.name
    if keys.github_handle:
        d["github_handle"] = keys.github_handle
    if keys.email:
        d["email"] = keys.email
    if keys.scholar_id:
        d["scholar_id"] = keys.scholar_id
    if keys.linkedin_url:
        d["linkedin_url"] = keys.linkedin_url
    return d


def _extract_json(text: str) -> dict | None:
    """Extract JSON from claude output, handling code fences and prose."""
    # Try direct parse first
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Find first { ... } block
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def research(
    keys: IdentityKeys,
    source_channel: str = "",
    source_url: str = "",
    raw_context: dict | None = None,
) -> Profile:
    """Run web research on a candidate via claude -p. Returns a Profile."""
    keys_dict = _build_keys_dict(keys)
    prompt = RESEARCH_PROMPT.format(
        keys_json=json.dumps(keys_dict, indent=2),
        source_channel=source_channel,
        source_url=source_url,
        context_json=json.dumps(raw_context or {}, indent=2),
    )

    print(f"  Researching {keys.strongest_key()}...")
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        print("  ERROR: 'claude' CLI not found. Install Claude Code.")
        return Profile(gaps=["claude CLI not available"])
    except subprocess.TimeoutExpired:
        print("  ERROR: claude -p timed out after 120s")
        return Profile(gaps=["research timed out"])

    if result.returncode != 0:
        print(f"  ERROR: claude -p failed: {result.stderr[:200]}")
        return Profile(gaps=[f"research failed: {result.stderr[:100]}"])

    data = _extract_json(result.stdout)
    if not data:
        print("  WARNING: Could not parse JSON from claude output")
        return Profile(
            summary=result.stdout[:500],
            gaps=["structured output parsing failed"],
        )

    return Profile(
        name=data.get("name"),
        confidence=float(data.get("confidence", 0)),
        location=data.get("location"),
        roles=data.get("roles", []),
        links=data.get("links", {}),
        summary=data.get("summary", ""),
        gaps=data.get("gaps", []),
        next_key_needed=data.get("next_key_needed"),
    )
