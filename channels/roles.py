"""Role-specific sourcing via claude -p web research.

Each role type has a tailored prompt that tells claude where to look
and what signals matter for that kind of hire.
"""

from __future__ import annotations

import json

from channels.company import _claude_prompt, _extract_json_array
from models import Candidate, IdentityKeys

WEB_SEARCH_PREAMBLE = """\
IMPORTANT: Use the WebSearch tool to find REAL people. Do NOT make up names \
or fabricate profiles. Search the web for each category of person listed below. \
If you cannot verify someone exists, do not include them.

"""

BATCH_SIZE = 10


def _parse_candidates(data: list[dict]) -> list[Candidate]:
    """Parse a list of dicts into Candidate objects."""
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
                source_channel=person.get("source_type", "role_search"),
                source_url=person.get("evidence_url", ""),
                raw_context={
                    "role": person.get("current_role", ""),
                    "company": person.get("company", ""),
                    "signal": person.get("why_interesting", ""),
                    "source_type": person.get("source_type", ""),
                },
            )
        )
    return candidates


def source_by_role(
    role_prompt: str, query: str, limit: int = 20
) -> list[Candidate]:
    """Generic role sourcing: send role-specific prompts to claude -p in batches."""
    all_candidates: list[Candidate] = []
    batches = max(1, (limit + BATCH_SIZE - 1) // BATCH_SIZE)

    for batch_num in range(batches):
        batch_limit = min(BATCH_SIZE, limit - len(all_candidates))
        if batch_limit <= 0:
            break

        prompt = WEB_SEARCH_PREAMBLE + role_prompt.format(
            query=query, limit=batch_limit
        )
        if batch_num > 0:
            # Tell subsequent batches to find different people
            already_found = ", ".join(
                c.keys.name for c in all_candidates if c.keys.name
            )
            prompt += (
                f"\n\nDo NOT include any of these people (already found): "
                f"{already_found}"
            )

        print(f"  Sourcing batch {batch_num + 1}/{batches} "
              f"({batch_limit} candidates)...")

        data = None
        for attempt in range(3):
            output = _claude_prompt(prompt)
            if not output:
                print(f"  WARNING: attempt {attempt + 1} failed, retrying...")
                continue
            data = _extract_json_array(output)
            if data:
                break
            print(f"  WARNING: attempt {attempt + 1} returned unparseable JSON, "
                  f"retrying...")

        if not data:
            print(f"  WARNING: Batch {batch_num + 1} failed after 3 attempts, "
                  f"continuing...")
            continue

        batch_candidates = _parse_candidates(data)
        all_candidates.extend(batch_candidates)
        print(f"    -> {len(batch_candidates)} candidates in this batch")

    print(f"  Found {len(all_candidates)} candidates total")
    return all_candidates
