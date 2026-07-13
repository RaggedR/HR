#!/usr/bin/env python3
"""Company HR — Product Manager headhunting."""

from cli_common import run_role_cli

SOURCE_PROMPT = """\
Find {limit} product managers who work on AI, governance, compliance, \
or supply chain technology products. Search the web for REAL people only.

Search focus: {query}

Look in these places:
- LinkedIn profiles of PMs at GRC platforms, supply chain SaaS, AI tooling companies
- Product Hunt launches in governance/compliance/supply chain space
- Blog posts and talks about building products for regulated industries
- Mind the Product, Lenny's Newsletter, or other PM community contributors
- Conference speakers at product events who focus on enterprise/B2B
- Glassdoor/Blind reviews mentioning strong PM leadership at relevant companies

Prioritize people who:
- Have shipped products for enterprise compliance, risk, or supply chain buyers
- Understand regulated industries (know what "auditable" means in product terms)
- Show user empathy for non-technical buyers (compliance officers, supply chain managers)
- Have experience translating complex technical capabilities into user-facing value
- Are at mid-career: senior enough to own a product area, hungry enough to join a startup

Return ONLY a JSON array (no prose, no markdown fences):
[
  {{
    "name": "Full Name",
    "linkedin_url": "https://linkedin.com/in/...",
    "github_handle": null,
    "email": null,
    "current_role": "Their current title and company",
    "company": "Current employer",
    "why_interesting": "Product sense, domain fit, career trajectory",
    "evidence_url": "Where you found them",
    "source_type": "linkedin/producthunt/blog/conference"
  }}
]
"""

if __name__ == "__main__":
    run_role_cli(
        role_name="product",
        description="Product Manager headhunting",
        source_prompt=SOURCE_PROMPT,
        default_query="AI governance supply chain enterprise product",
    )
