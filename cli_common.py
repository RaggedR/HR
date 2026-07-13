"""Shared CLI infrastructure for role-specific headhunting tools."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from channels.roles import source_by_role
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


def enrich_candidate(candidate: Candidate, role_context: str = "") -> Dossier:
    """Run the full enrichment pipeline on a candidate."""
    if role_context:
        candidate.raw_context["role_context"] = role_context

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
        sources=[candidate.source_url],
        source_channels=[candidate.source_channel],
        highest_breakout_score=candidate.breakout_score,
    )

    if not dossier.keys.name and profile.name:
        dossier.keys.name = profile.name

    dossier.compute_rank()
    return dossier


def run_role_cli(
    role_name: str,
    description: str,
    source_prompt: str,
    default_query: str = "",
) -> None:
    """Build and run a role-specific CLI."""
    parser = argparse.ArgumentParser(
        description=f"Company HR — {description}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subs = parser.add_subparsers(dest="command", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--format", "-f", choices=["terminal", "json", "pdf"], default="pdf"
    )
    shared.add_argument(
        "--output", "-o", help="Output PDF path (default: data/candidates_<timestamp>.pdf)"
    )
    shared.add_argument("--no-enrich", action="store_true")
    shared.add_argument("--enrich-limit", type=int, default=10)

    # search
    p_search = subs.add_parser(
        "search", parents=[shared], help=f"Find {role_name} candidates",
    )
    p_search.add_argument(
        "query", nargs="?", default=default_query,
        help=f"Search focus (default: '{default_query}')",
    )
    p_search.add_argument("--limit", "-n", type=int, default=10)
    p_search.add_argument(
        "--from-companies", action="store_true",
        help="Source candidates from the target company list instead of open web search",
    )

    # direct
    p_direct = subs.add_parser(
        "direct", parents=[shared], help="Look up a specific person",
    )
    p_direct.add_argument("name", nargs="?", help="Person's name")
    p_direct.add_argument("--github", help="GitHub handle")
    p_direct.add_argument("--email", help="Email address")
    p_direct.add_argument("--linkedin", help="LinkedIn URL")

    # list
    p_list = subs.add_parser(
        "list", parents=[shared], help="List cached dossiers",
    )
    p_list.add_argument("--min-confidence", type=float)

    # show
    p_show = subs.add_parser(
        "show", parents=[shared], help="Show a specific dossier",
    )
    p_show.add_argument("name", help="Name or identifier")

    # offer
    p_offer = subs.add_parser(
        "offer", parents=[shared],
        help="Generate offer letters for cached dossiers",
    )
    p_offer.add_argument(
        "names", nargs="*",
        help="Names to generate letters for (default: all cached dossiers)",
    )

    args = parser.parse_args()

    if args.command == "search":
        if getattr(args, "from_companies", False):
            from channels.company import find_people_by_role
            from output.store import load_companies

            companies = load_companies()
            if not companies:
                print("No target companies. Run: python companies.py discover \"query\"")
                return
            print(f"{description} (from {len(companies)} target companies)\n")
            candidates = []
            for company in companies:
                candidates.extend(find_people_by_role(company, role_name))
            candidates = deduplicate(candidates)
        else:
            print(f"{description}: '{args.query}'\n")
            candidates = source_by_role(source_prompt, args.query, args.limit)
            candidates = deduplicate(candidates)
        print(render_candidate_table(candidates))

        if not args.no_enrich:
            _enrich_and_display(candidates, args, role_name)

    elif args.command == "direct":
        from channels.direct import lookup
        candidate = lookup(
            name=args.name,
            github=getattr(args, "github", None),
            email=getattr(args, "email", None),
            linkedin=getattr(args, "linkedin", None),
        )
        print(f"Direct lookup: {candidate.keys.strongest_key()}")
        if args.no_enrich:
            print(render_candidate_table([candidate]))
        else:
            dossier = enrich_candidate(candidate, role_context=role_name)
            path = save_dossier(dossier)
            print(render_dossier(dossier))
            print(f"\n  Saved to {path}")

    elif args.command == "list":
        dossiers = list_dossiers()
        if args.min_confidence:
            dossiers = [
                d for d in dossiers if d.profile.confidence >= args.min_confidence
            ]
        dossiers.sort(key=lambda d: d.rank_score, reverse=True)
        if not dossiers:
            print("No dossiers found.")
        else:
            print(render_dossier_table(dossiers))

    elif args.command == "show":
        dossier = find_dossier_by_name(args.name)
        if not dossier:
            print(f"No dossier found matching '{args.name}'")
        elif args.format == "json":
            print(json.dumps(asdict(dossier), indent=2))
        else:
            print(render_dossier(dossier))

    elif args.command == "offer":
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
        else:
            pdf_path = generate_offer_letter(
                dossiers,
                role=role_name,
                output_path=getattr(args, "output", None),
            )
            print(f"  Offer letters generated: {pdf_path}")
            print(f"  {len(dossiers)} candidates")
            sp.run(["open", "-a", "Skim", str(pdf_path)])


def _enrich_and_display(
    candidates: list[Candidate],
    args: argparse.Namespace,
    role_context: str,
) -> None:
    to_enrich = candidates[: args.enrich_limit]
    print(f"\n--- Enriching {len(to_enrich)} candidates ---")
    dossiers = []
    for i, candidate in enumerate(to_enrich, 1):
        print(f"\n[{i}/{len(to_enrich)}] {candidate.keys.strongest_key()}")
        dossier = enrich_candidate(candidate, role_context=role_context)
        path = save_dossier(dossier)
        dossiers.append(dossier)
        print(f"  -> confidence: {dossier.profile.confidence:.0%}, saved to {path}")

    dossiers.sort(key=lambda d: d.rank_score, reverse=True)
    print("\n\n=== RESULTS ===")
    if args.format == "json":
        print(json.dumps([asdict(d) for d in dossiers], indent=2))
    elif args.format == "pdf":
        from output.pdf import generate_pdf
        pdf_path = generate_pdf(dossiers, output_path=getattr(args, "output", None))
        print(f"\n  PDF generated: {pdf_path}")
        import subprocess
        subprocess.run(["open", "-a", "Skim", str(pdf_path)])
    else:
        for d in dossiers:
            print(render_dossier(d))
