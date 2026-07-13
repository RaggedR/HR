#!/usr/bin/env python3
"""Company HR — Domain Expert headhunting (supply chain + AI governance)."""

from cli_common import run_role_cli

SOURCE_PROMPT = """\
Find {limit} domain experts in AI governance and/or supply chain management \
who could bring deep industry knowledge to a technology company. \
Search the web for REAL people only.

Search focus: {query}

Look in these places:
- Authors of industry reports (McKinsey, Deloitte, Gartner, Forrester) on \
AI governance or supply chain transformation
- Regulatory body working group members (EU AI Act consultants, NIST AI RMF contributors)
- Supply chain industry association leaders (ASCM, CSCMP, GS1)
- Keynote speakers at supply chain conferences (Gartner Supply Chain Symposium, \
CSCMP EDGE, MIT CTL events)
- Substack/newsletter writers on responsible AI, supply chain resilience
- University researchers doing applied (not purely theoretical) work on \
AI governance or supply chain optimization
- Former heads of supply chain at major companies now consulting

Prioritize people who:
- Bridge the gap between technical AI and business/regulatory supply chain needs
- Have published or spoken about AI governance IN supply chain contexts specifically
- Are practitioners (not purely academic) who've implemented governance frameworks
- Show rising influence (invited to more/bigger events, growing readership)
- Would be credible to both the technical team and enterprise customers

Return ONLY a JSON array (no prose, no markdown fences):
[
  {{
    "name": "Full Name",
    "linkedin_url": "https://linkedin.com/in/...",
    "github_handle": null,
    "email": null,
    "current_role": "Their current title and organization",
    "company": "Current organization",
    "why_interesting": "Domain depth, bridge value, credibility signal",
    "evidence_url": "Link to their best publication, talk, or profile",
    "source_type": "publication/conference/association/newsletter/linkedin"
  }}
]
"""

if __name__ == "__main__":
    run_role_cli(
        role_name="domain_expert",
        description="Domain Expert headhunting (supply chain + AI governance)",
        source_prompt=SOURCE_PROMPT,
        default_query="AI governance supply chain regulation compliance",
    )
