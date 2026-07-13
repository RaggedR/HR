#!/usr/bin/env python3
"""Company HR Headhunting Tool.

Finds rising candidates via contrarian search, company discovery,
and direct lookup, then enriches them with Rolo-style web research.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from channels import direct
from channels.company import search as company_search
from channels.contrarian import search_all as contrarian_search
from dedup import deduplicate
from enrichment.confidence import blend
from enrichment.refute import refute
from enrichment.research import research
from models import Candidate, Dossier
from output.store import find_dossier_by_name, list_dossiers, save_dossier
from output.terminal import (
    render_candidate_table,
    render_dossier,
    render_dossier_table,
)


def enrich_candidate(candidate: Candidate) -> Dossier:
    """Run the full enrichment pipeline on a candidate."""
    profile = research(
        candidate.keys,
        source_channel=candidate.source_channel,
        source_url=candidate.source_url,
        raw_context=candidate.raw_context,
    )
    verification = refute(candidate.keys)
    blend(profile, verification)

    dossier = Dossier(
        keys=candidate.keys,
        profile=profile,
        verification=verification,
        sources=[candidate.source_url]
        + candidate.raw_context.get("all_sources", []),
        source_channels=candidate.source_channel.split(", "),
        highest_breakout_score=candidate.breakout_score,
    )

    # Update name from research if we didn't have one
    if not dossier.keys.name and profile.name:
        dossier.keys.name = profile.name

    dossier.compute_rank()
    return dossier


def cmd_contrarian(args: argparse.Namespace) -> None:
    """Run contrarian search across GitHub + Scholar.

    Splits multi-word queries into sub-queries for broader coverage,
    since API search works better with focused terms.
    """
    # Split on commas or use the full query if no commas
    if "," in args.query:
        sub_queries = [q.strip() for q in args.query.split(",") if q.strip()]
    else:
        sub_queries = [args.query]

    print(f"Contrarian search: {sub_queries}")
    print(f"  max_popularity={args.max_pop}, days={args.days}, limit={args.limit}")

    async def _multi_search():
        all_candidates = []
        for q in sub_queries:
            print(f"\n  Searching: '{q}'")
            results = await contrarian_search(q, args.max_pop, args.days, args.limit)
            all_candidates.extend(results)
            print(f"    -> {len(results)} candidates")
        return all_candidates

    candidates = asyncio.run(_multi_search())
    candidates = deduplicate(candidates)
    print(render_candidate_table(candidates))

    if not args.no_enrich:
        _enrich_and_display(candidates, args)


def cmd_company(args: argparse.Namespace) -> None:
    """Run company discovery channel."""
    print(f"Company discovery: '{args.query}'")
    candidates = company_search(args.query, limit=args.limit)
    candidates = deduplicate(candidates)
    print(render_candidate_table(candidates))

    if not args.no_enrich:
        _enrich_and_display(candidates, args)


def cmd_direct(args: argparse.Namespace) -> None:
    """Direct person lookup."""
    candidate = direct.lookup(
        name=args.name,
        github=args.github,
        email=args.email,
        scholar_id=args.scholar_id,
        linkedin=args.linkedin,
    )
    print(f"Direct lookup: {candidate.keys.strongest_key()}")

    if args.no_enrich:
        print(render_candidate_table([candidate]))
    else:
        dossier = enrich_candidate(candidate)
        path = save_dossier(dossier)
        print(render_dossier(dossier))
        print(f"\n  Saved to {path}")


def cmd_search(args: argparse.Namespace) -> None:
    """Run all channels and merge."""
    all_candidates: list[Candidate] = []

    print(f"Full search: '{args.query}'\n")

    print("--- Channel 1: Contrarian Search ---")
    contrarian = asyncio.run(
        contrarian_search(args.query, args.max_pop, args.days, args.limit)
    )
    all_candidates.extend(contrarian)
    print(f"  {len(contrarian)} candidates from contrarian search")

    print("\n--- Channel 2: Company Discovery ---")
    company = company_search(args.query, limit=args.company_limit)
    all_candidates.extend(company)
    print(f"  {len(company)} candidates from company discovery")

    print(f"\n--- Deduplicating {len(all_candidates)} candidates ---")
    candidates = deduplicate(all_candidates)
    print(f"  {len(candidates)} unique candidates")

    print(render_candidate_table(candidates))

    if not args.no_enrich:
        _enrich_and_display(candidates, args)


def cmd_offer(args: argparse.Namespace) -> None:
    """Generate offer letters for cached dossiers."""
    import subprocess as sp
    from output.offer_letter import generate_offer_letter

    if args.names:
        dossiers = []
        for name in args.names:
            d = find_dossier_by_name(name)
            if d:
                dossiers.append(d)
            else:
                print(f"  No dossier found matching '{name}'")
    else:
        dossiers = list_dossiers()

    if not dossiers:
        print("No dossiers to generate offer letters for.")
        return

    pdf_path = generate_offer_letter(
        dossiers,
        role="technical",
        output_path=getattr(args, "output", None),
    )
    print(f"  Offer letters generated: {pdf_path}")
    print(f"  {len(dossiers)} candidates")
    sp.run(["open", "-a", "Skim", str(pdf_path)])


def cmd_list(args: argparse.Namespace) -> None:
    """List cached dossiers."""
    dossiers = list_dossiers()
    if args.min_confidence:
        dossiers = [
            d for d in dossiers if d.profile.confidence >= args.min_confidence
        ]
    dossiers.sort(key=lambda d: d.rank_score, reverse=True)
    if not dossiers:
        print("No dossiers found. Run a search first.")
        return
    print(render_dossier_table(dossiers))


def cmd_show(args: argparse.Namespace) -> None:
    """Show a specific dossier."""
    dossier = find_dossier_by_name(args.name)
    if not dossier:
        print(f"No dossier found matching '{args.name}'")
        return
    if args.format == "json":
        print(json.dumps(asdict(dossier), indent=2))
    elif args.format == "pdf":
        from output.pdf import generate_pdf
        import subprocess as sp
        pdf_path = generate_pdf([dossier], output_path=getattr(args, "output", None))
        print(f"  PDF: {pdf_path}")
        sp.run(["open", "-a", "Skim", str(pdf_path)])
    else:
        print(render_dossier(dossier))


def _enrich_and_display(candidates: list[Candidate], args: argparse.Namespace) -> None:
    """Enrich candidates and display/save results."""
    enrich_limit = getattr(args, "enrich_limit", len(candidates))
    to_enrich = candidates[:enrich_limit]

    print(f"\n--- Enriching {len(to_enrich)} candidates ---")
    dossiers = []
    for i, candidate in enumerate(to_enrich, 1):
        print(f"\n[{i}/{len(to_enrich)}] {candidate.keys.strongest_key()}")
        dossier = enrich_candidate(candidate)
        path = save_dossier(dossier)
        dossiers.append(dossier)
        print(f"  -> confidence: {dossier.profile.confidence:.0%}, saved to {path}")

    dossiers.sort(key=lambda d: d.rank_score, reverse=True)
    print("\n\n=== RESULTS ===")

    if args.format == "json":
        print(json.dumps([asdict(d) for d in dossiers], indent=2))
    elif args.format == "pdf":
        from output.pdf import generate_pdf
        import subprocess as sp
        pdf_path = generate_pdf(dossiers, output_path=getattr(args, "output", None))
        print(f"\n  PDF generated: {pdf_path}")
        sp.run(["open", "-a", "Skim", str(pdf_path)])
    else:
        for d in dossiers:
            print(render_dossier(d))


def main() -> None:
    # Shared flags inherited by all subcommands
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--format", "-f", choices=["terminal", "json", "pdf"], default="pdf"
    )
    shared.add_argument(
        "--output", "-o", help="Output PDF path"
    )
    shared.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip enrichment (output raw candidates only)",
    )
    shared.add_argument(
        "--enrich-limit",
        type=int,
        default=10,
        help="Max candidates to enrich (default: 10)",
    )

    parser = argparse.ArgumentParser(
        description="Company HR Headhunting Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s contrarian "AI governance supply chain"
  %(prog)s company "AI governance Lean agentic"
  %(prog)s direct "Jane Smith" --github jsmith42
  %(prog)s search "AI governance supply chain" --no-enrich
  %(prog)s list --min-confidence 0.5
  %(prog)s show "Jane Smith"
""",
    )

    subs = parser.add_subparsers(dest="command", required=True)

    # contrarian
    p_con = subs.add_parser(
        "contrarian", parents=[shared],
        help="Contrarian search (GitHub + Scholar)",
    )
    p_con.add_argument("query", help="Search keywords")
    p_con.add_argument("--max-pop", type=int, default=500)
    p_con.add_argument("--days", type=int, default=60)
    p_con.add_argument("--limit", "-n", type=int, default=20)
    p_con.set_defaults(func=cmd_contrarian)

    # company
    p_co = subs.add_parser(
        "company", parents=[shared],
        help="Company discovery → extract engineers",
    )
    p_co.add_argument("query", help="Search keywords")
    p_co.add_argument("--limit", "-n", type=int, default=10)
    p_co.set_defaults(func=cmd_company)

    # direct
    p_dir = subs.add_parser(
        "direct", parents=[shared], help="Direct person lookup",
    )
    p_dir.add_argument("name", nargs="?", help="Person's name")
    p_dir.add_argument("--github", help="GitHub handle")
    p_dir.add_argument("--email", help="Email address")
    p_dir.add_argument("--scholar-id", help="Semantic Scholar author ID")
    p_dir.add_argument("--linkedin", help="LinkedIn URL")
    p_dir.set_defaults(func=cmd_direct)

    # search (all channels)
    p_search = subs.add_parser(
        "search", parents=[shared], help="All channels combined",
    )
    p_search.add_argument("query", help="Search keywords")
    p_search.add_argument("--max-pop", type=int, default=500)
    p_search.add_argument("--days", type=int, default=60)
    p_search.add_argument("--limit", "-n", type=int, default=20)
    p_search.add_argument("--company-limit", type=int, default=5)
    p_search.set_defaults(func=cmd_search)

    # list
    p_list = subs.add_parser(
        "list", parents=[shared], help="List cached dossiers",
    )
    p_list.add_argument("--min-confidence", type=float)
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = subs.add_parser(
        "show", parents=[shared], help="Show a specific dossier",
    )
    p_show.add_argument("name", help="Name or GitHub handle to search for")
    p_show.set_defaults(func=cmd_show)

    # offer
    p_offer = subs.add_parser(
        "offer", parents=[shared],
        help="Generate offer letters for cached dossiers",
    )
    p_offer.add_argument(
        "names", nargs="*",
        help="Names to generate letters for (default: all)",
    )
    p_offer.set_defaults(func=cmd_offer)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
