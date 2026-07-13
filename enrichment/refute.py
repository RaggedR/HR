"""Adversarial refute pass: try to disprove the candidate identity."""

from __future__ import annotations

import json
import subprocess

from enrichment.research import _build_keys_dict, _extract_json
from models import IdentityKeys, Verification

REFUTE_PROMPT = """\
You are a skeptical fact-checker reviewing a candidate identity claim.

## Claimed Identity Keys
{keys_json}

## Your Task
Search the web and try to DISPROVE or CAST DOUBT on this identity. Look for:
1. Name collisions — other people with the same name in similar fields
2. Abandoned or fake GitHub accounts
3. Stale profiles (person left the field years ago)
4. Inconsistencies between GitHub activity and claimed roles
5. Any evidence this is not a single person (e.g., shared account, org account)

Be thorough but fair. If you find no issues, say so honestly.

## Output
Return ONLY a JSON object (no markdown fences, no prose):
{{
  "confirmed": true,
  "confidence_cap": 0.9,
  "refute_notes": "What you found. Be specific. Cite URLs if possible."
}}

Set confirmed=false and lower confidence_cap if you find real problems.
"""


def refute(keys: IdentityKeys) -> Verification:
    """Run adversarial refute pass via claude -p."""
    keys_dict = _build_keys_dict(keys)
    prompt = REFUTE_PROMPT.format(
        keys_json=json.dumps(keys_dict, indent=2),
    )

    print(f"  Refuting {keys.strongest_key()}...")
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return Verification(
            confirmed=False,
            confidence_cap=0.5,
            refute_notes=f"refute pass failed: {e}",
        )

    if result.returncode != 0:
        return Verification(
            confirmed=False,
            confidence_cap=0.5,
            refute_notes=f"refute pass error: {result.stderr[:200]}",
        )

    data = _extract_json(result.stdout)
    if not data:
        return Verification(
            confirmed=False,
            confidence_cap=0.5,
            refute_notes="could not parse refute output",
        )

    return Verification(
        confirmed=bool(data.get("confirmed", False)),
        confidence_cap=float(data.get("confidence_cap", 0.5)),
        refute_notes=data.get("refute_notes", ""),
    )
