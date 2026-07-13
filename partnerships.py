#!/usr/bin/env python3
"""Company HR — Business Development / Partnerships headhunting."""

from cli_common import run_role_cli

SOURCE_PROMPT = """\
Find {limit} business development and partnerships professionals who build \
channel partnerships and technology alliances in the Middle East, Africa, or \
South Asia. Search the web for REAL people only.

Search focus: {query}

Look in these places:
- LinkedIn profiles of partnerships/alliances leads at IT service providers \
operating in UAE, Saudi Arabia, Qatar (e.g. local system integrators, sovereign \
cloud providers, digital transformation consultancies in the Gulf)
- People at companies like Injazat, G42, Tonomus, Gulf Business Machines, \
Etisalat Digital, STC Solutions, Elm, Tahakom who manage technology partnerships
- Press releases about AI or enterprise tech partnerships in MENA
- GITEX Global, LEAP, Arab Future Cities Summit speaker/panelist lists
- People who have built channel/reseller networks for Western tech companies \
entering Gulf or African markets
- BD leads at companies selling into sovereign entities or government-linked enterprises

Prioritize people who:
- Have built channel partnerships between Western technology companies and \
Gulf/African IT service providers or system integrators
- Understand sovereign AI requirements and local data residency constraints
- Have navigated government procurement and sovereign entity relationships
- Come from the enterprise AI, industrial tech, or supply chain technology space
- Have a rolodex in Dubai, Riyadh, Abu Dhabi, Doha, or major African business hubs
- Are comfortable with long relationship-building cycles and cultural nuance

Return ONLY a JSON array (no prose, no markdown fences):
[
  {{
    "name": "Full Name",
    "linkedin_url": "https://linkedin.com/in/...",
    "github_handle": null,
    "email": null,
    "current_role": "Their current title and company",
    "company": "Current employer",
    "why_interesting": "Channel access, sovereign AI experience, regional network",
    "evidence_url": "Where you found them",
    "source_type": "linkedin/press_release/conference/team_page"
  }}
]
"""

if __name__ == "__main__":
    run_role_cli(
        role_name="partnerships",
        description="Business Development / Partnerships headhunting",
        source_prompt=SOURCE_PROMPT,
        default_query="MENA sovereign AI channel partnerships Gulf system integrators",
    )
