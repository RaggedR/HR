#!/usr/bin/env python3
"""Company HR — Customer Relations headhunting."""

from cli_common import run_role_cli

SOURCE_PROMPT = """\
Find {limit} customer success or account management professionals who manage \
enterprise deployments of AI platforms, industrial software, or supply chain \
technology — ideally with experience in the Middle East, Africa, or South Asia. \
Search the web for REAL people only.

Search focus: {query}

Look in these places:
- LinkedIn profiles of CSMs and account directors at enterprise AI or supply chain \
platforms deployed in MENA (companies like Palantir, C3.ai, o9 Solutions, Kinaxis, \
Blue Yonder, FourKites, SAP, Oracle SCM)
- People who manage accounts at manufacturing, logistics, or industrial companies \
— especially multi-facility deployments across countries
- Customer success leaders at companies with Gulf or African enterprise customers
- Case study presenters at supply chain or industrial AI conferences
- People at companies like Siemens, ABB, Honeywell, Rockwell who manage industrial \
software deployments in emerging markets

Prioritize people who:
- Manage a small number of high-value enterprise accounts (not self-serve SaaS)
- Have experience with multi-facility industrial deployments (manufacturing, \
supply chain, production monitoring)
- Understand cross-cultural enterprise relationships, especially Gulf business culture
- Have managed complex onboarding involving supply chain workflows, procurement, \
or production systems
- Show strong client advocacy and expansion track record
- Are comfortable being the primary relationship holder with C-suite sponsors
- Have domain knowledge in supply chain, manufacturing, or logistics

Return ONLY a JSON array (no prose, no markdown fences):
[
  {{
    "name": "Full Name",
    "linkedin_url": "https://linkedin.com/in/...",
    "github_handle": null,
    "email": null,
    "current_role": "Their current title and company",
    "company": "Current employer",
    "why_interesting": "Enterprise account management, industrial domain, regional experience",
    "evidence_url": "Where you found them",
    "source_type": "linkedin/case_study/conference/team_page"
  }}
]
"""

if __name__ == "__main__":
    run_role_cli(
        role_name="customer_relations",
        description="Customer Relations headhunting",
        source_prompt=SOURCE_PROMPT,
        default_query="enterprise AI customer success MENA industrial supply chain",
    )
