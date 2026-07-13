# CLAUDE.md

Company HR headhunting suite. Finds and enriches candidates for all roles.

## Stack
- Python 3, async (httpx)
- Contrarian search engine at ~/git/search/ (imported for technical roles)
- Enrichment via headless `claude -p` (Rolo-style: research + adversarial refute)

## Tools

### Technical roles (API-driven sourcing + enrichment)
```bash
python hr.py contrarian "AI governance supply chain" --no-enrich   # dry run
python hr.py company "AI governance Lean agentic"                  # find companies → engineers
python hr.py direct "Jane Smith" --github jsmith42                 # single person
python hr.py search "AI governance Lean agentic"                   # all channels
```

### Business roles (claude -p sourced + enrichment)
```bash
python sales.py search "AI governance supply chain"
python marketing.py search "AI governance B2B content"
python customer_success.py search "AI governance enterprise"  # customer relations
python partnerships.py search "supply chain integration"
python domain_expert.py search "AI governance regulation"
python product.py search "AI governance supply chain"
```

### Offer letters
```bash
python <tool>.py offer                         # all cached dossiers
python <tool>.py offer "Jane Smith"            # specific candidate
python hr.py offer -o report.pdf               # custom output path
```

### Shared commands (all tools)
```bash
python <tool>.py list                          # cached dossiers
python <tool>.py show "Jane Smith"             # one dossier
python <tool>.py direct "Jane Smith"           # direct lookup
python <tool>.py search "query" --no-enrich    # sourcing only, skip enrichment
```

## Architecture
- `hr.py` — technical roles CLI (contrarian search + company discovery)
- `sales.py`, `marketing.py`, `customer_success.py`, `partnerships.py`, `domain_expert.py`, `product.py` — business role CLIs
- `cli_common.py` — shared CLI infrastructure for role tools
- `channels/` — sourcing channels (contrarian, company, direct, roles)
- `enrichment/` — Rolo-style research + adversarial refute + confidence blending
- `output/` — terminal display + JSON store in `data/` + offer letter PDF
- `output/offer_letter.py` — personalised offer letters with personality-fit questions
- `dedup.py` — identity key deduplication
- `models.py` — all dataclasses

## Rules
- NEVER send emails automatically
- Enrichment uses `claude -p` (zero marginal cost on Max plan)
- Confidence scoring is honest: gaps and unknowns are first-class
- Data stays local in `data/` (gitignored)
