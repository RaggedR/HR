# HR Headhunting Suite

Finds and enriches candidates for all roles. Sourcing via `claude -p` web search, enrichment via research + adversarial refute pipeline.

## Quick Start

```bash
pip install -r requirements.txt
```

## CLI Tools

### Technical roles

```bash
python hr.py contrarian "AI governance supply chain" --no-enrich   # dry run
python hr.py company "AI governance Lean agentic"                  # find companies -> engineers
python hr.py direct "Jane Smith" --github jsmith42                 # single person
python hr.py search "AI governance Lean agentic"                   # all channels
```

### Target company list

```bash
python companies.py discover "enterprise AI supply chain MENA Gulf"  # find target companies
python companies.py list                                              # show target list
python companies.py show "Palantir"                                   # details on one company
python companies.py add "Acme Corp" -w https://acme.com -r Gulf       # manually add
python companies.py remove "Acme Corp"                                # remove from list
python companies.py source "Palantir" --role sales                    # find sales people at Palantir
python companies.py source-all --role sales                           # find sales people at ALL targets
```

### Non-technical roles

```bash
python sales.py search "enterprise AI sales MENA Gulf conglomerates"
python marketing.py search "deep tech marketing AI governance"
python customer_success.py search "enterprise AI customer success MENA"
python partnerships.py search "MENA sovereign AI channel partnerships"
python domain_expert.py search "AI governance regulation"
python product.py search "AI governance supply chain"
```

Any role tool can also source from the target company list:

```bash
python sales.py search --from-companies --no-enrich    # source from target list
```

### Common commands (all tools)

```bash
python <tool>.py search "query"                # source + enrich, output PDF
python <tool>.py search "query" --no-enrich    # sourcing only, skip enrichment
python <tool>.py search "query" --limit 10     # number of candidates to source
python <tool>.py direct "Jane Smith"            # direct lookup + enrich
python <tool>.py list                           # cached dossiers
python <tool>.py show "Jane Smith"              # one dossier
python <tool>.py offer                          # offer letters for all cached dossiers
python <tool>.py offer "Jane Smith"             # offer letter for one candidate
```

### Output options

```bash
python <tool>.py search "query" -o data/my-report.pdf   # custom PDF path
python <tool>.py search "query" -f terminal              # terminal output instead of PDF
python <tool>.py search "query" -f json                  # JSON output
```

### Pretty PDF

```bash
python pretty_pdf.py input.pdf -o output.pdf    # Penrose tiling + wrought-iron border
python pretty_pdf.py input.pdf --border-only    # border only
python pretty_pdf.py input.pdf --tiling-only    # tiling only
```

## Architecture

```
hr.py                  Technical roles CLI (contrarian search + company discovery)
companies.py           Target company list management + company-first sourcing
sales.py               Enterprise Sales sourcing (MENA / Gulf / conglomerates)
marketing.py           Marketing sourcing (deep tech / category creation)
customer_success.py    Customer Success sourcing (industrial deployments / MENA)
partnerships.py        Partnerships sourcing (Gulf channel / sovereign AI)
domain_expert.py       Domain Expert sourcing
product.py             Product sourcing
cli_common.py          Shared CLI infrastructure
models.py              All dataclasses
dedup.py               Identity key deduplication
pretty_pdf.py          Decorative PDF overlay

channels/              Sourcing channels
  contrarian.py          Contrarian search engine integration
  company.py             Company discovery -> engineer extraction
  direct.py              Direct person lookup
  roles.py               Role-specific sourcing via claude -p

enrichment/            Enrichment pipeline
  research.py            Web research via claude -p
  refute.py              Adversarial identity refutation via claude -p
  confidence.py          Confidence score blending

output/                Output generation
  pdf.py                 PDF dossier generation (one page per candidate)
  offer_letter.py        Personalised offer letters
  store.py               JSON dossier storage in data/
  terminal.py            Terminal display

data/                  All output (PDFs, JSON dossiers) — gitignored
```

## How It Works

1. **Source** — `claude -p` with web search finds real candidates matching role-specific criteria
2. **Deduplicate** — Identity keys (name, GitHub, LinkedIn, email) collapse duplicates
3. **Research** — `claude -p` builds a structured profile from web evidence
4. **Refute** — A second `claude -p` pass tries to disprove the identity (name collisions, stale profiles, fake accounts)
5. **Blend** — Confidence scores are capped by refutation findings
6. **Output** — PDF with one page per candidate, sorted by rank score
