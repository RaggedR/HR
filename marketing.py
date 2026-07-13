#!/usr/bin/env python3
"""Company HR — Marketing headhunting."""

from cli_common import run_role_cli

SOURCE_PROMPT = """\
Find {limit} marketing professionals who can translate deep tech or novel \
mathematics-based technology into compelling enterprise narratives. \
Search the web for REAL people only.

Search focus: {query}

Look in these places:
- Marketing leaders at deep tech companies that sell complex/novel technology \
(not commodity SaaS) — companies like Palantir, Anduril, Cerebras, DeepMind, \
Anthropic, Cohere, Scale AI, or similar
- People who have marketed formal verification, cryptography, or mathematically \
rigorous products to enterprise buyers
- Content marketers who write about AI safety, AI governance, or responsible AI \
for business audiences (not just academic audiences)
- Marketing leaders at supply chain tech companies (Altana AI, Resilinc, FourKites, \
Everstream Analytics, Sourcemap) who understand industrial buyers
- People at B2B deep tech companies who built thought leadership from scratch \
(analyst relations, conference strategy, executive ghostwriting)
- Marketers experienced with MENA or emerging market positioning

Prioritize people who:
- Can make unfamiliar technology feel inevitable rather than exotic
- Have marketed to C-suite at industrial companies, conglomerates, or sovereign entities
- Understand regulatory-driven demand (compliance as a wedge into enterprise deals)
- Have experience building a category (not just marketing within an existing one)
- Show content that translates mathematical or deeply technical concepts for executives
- Have worked at early-stage deep tech companies (not just mature SaaS)

Return ONLY a JSON array (no prose, no markdown fences):
[
  {{
    "name": "Full Name",
    "linkedin_url": "https://linkedin.com/in/...",
    "github_handle": null,
    "email": null,
    "current_role": "Their current title and company",
    "company": "Current employer",
    "why_interesting": "Category creation ability, deep tech storytelling, relevant verticals",
    "evidence_url": "Link to their best content or profile",
    "source_type": "blog/newsletter/twitter/conference/linkedin"
  }}
]
"""

if __name__ == "__main__":
    run_role_cli(
        role_name="marketing",
        description="Marketing headhunting",
        source_prompt=SOURCE_PROMPT,
        default_query="deep tech marketing AI governance enterprise category creation",
    )
