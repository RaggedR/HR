#!/usr/bin/env python3
"""Company HR — Enterprise Sales headhunting."""

from cli_common import run_role_cli

SOURCE_PROMPT = """\
Find {limit} enterprise sales professionals who sell deep tech, AI platforms, \
or industrial technology to large conglomerates, family-owned industrial groups, \
or sovereign entities in the Middle East, Africa, India, or Southeast Asia. \
Search the web for REAL people only.

Search focus: {query}

Look in these places:
- LinkedIn profiles of enterprise sales leaders at companies selling into MENA \
(UAE, Saudi Arabia, Qatar) — especially AI, industrial software, or supply chain tech
- Team pages of companies like Palantir, C3.ai, o9 Solutions, Kinaxis, Blue Yonder, \
FourKites, project44, Altana AI, Resilinc that sell to large industrial enterprises
- Speaker lists from GITEX Global (Dubai), LEAP (Riyadh), World Government Summit, \
Gartner Supply Chain Symposium, ADIPEC
- Press releases about enterprise AI deals in the Gulf or Africa
- People who have sold to conglomerates like Dangote, Adani, SABIC, Aramco, \
Emirates Steel, Ma'aden, or similar vertically integrated groups

Prioritize people who:
- Have closed deals with founder-controlled conglomerates or sovereign entities
- Sell complex, high-value solutions (not volume SaaS — think $500K+ deals)
- Are based in or have deep networks in Dubai, Riyadh, Abu Dhabi, or Doha
- Have experience with 6-18 month enterprise sales cycles into industrial verticals
- Understand supply chain, manufacturing, logistics, or compliance buying centres
- Can sell novel/unfamiliar technology (not just another CRM or ERP reskin)
- Come from deep tech or industrial AI companies, not generic SaaS

Return ONLY a JSON array (no prose, no markdown fences):
[
  {{
    "name": "Full Name",
    "linkedin_url": "https://linkedin.com/in/...",
    "github_handle": null,
    "email": null,
    "current_role": "Their current title and company",
    "company": "Current employer",
    "why_interesting": "Why this person stands out — deal size, region, conglomerate access",
    "evidence_url": "Where you found them",
    "source_type": "linkedin/conference/press_release/team_page"
  }}
]
"""

if __name__ == "__main__":
    run_role_cli(
        role_name="sales",
        description="Enterprise Sales headhunting",
        source_prompt=SOURCE_PROMPT,
        default_query="enterprise AI sales MENA Gulf conglomerates supply chain",
    )
