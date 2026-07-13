#!/usr/bin/env python3
"""Company HR — Target company list management.

Headhunters work company-first: find 20 companies in your space, then poach
their people by role. This tool manages the persistent target company list
and sources candidates from it.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from channels.company import discover_companies, find_people_by_role
from dedup import deduplicate
from models import CompanyProfile
from output.store import (
    add_company,
    find_company_by_name,
    load_companies,
    remove_company,
    save_companies,
)


def _render_company_table(companies: list[CompanyProfile]) -> str:
    lines = [
        f"  {'#':>3}  {'Name':<30} {'Region':<12} {'Description'}",
        "  " + "-" * 90,
    ]
    for i, c in enumerate(companies, 1):
        desc = c.description[:45] + "..." if len(c.description) > 48 else c.description
        lines.append(f"  {i:>3}  {c.name:<30} {c.region:<12} {desc}")
    lines.append("  " + "-" * 90)
    lines.append(f"  {len(companies)} companies")
    return "\n".join(lines)


def _render_company_detail(c: CompanyProfile) -> str:
    lines = [
        f"\n  {c.name}",
        f"  {'=' * len(c.name)}",
        f"  Website:     {c.website}",
        f"  Region:      {c.region or 'unknown'}",
    ]
    if c.github_org:
        lines.append(f"  GitHub org:  {c.github_org}")
    lines.append(f"  Description: {c.description}")
    lines.append(f"  Relevance:   {c.relevance}")
    lines.append(f"  Added:       {c.added_at[:10]}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Company HR — Target company list",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subs = parser.add_subparsers(dest="command", required=True)

    # discover
    p_disc = subs.add_parser("discover", help="Find target companies via web search")
    p_disc.add_argument("query", help="Search focus for company discovery")

    # list
    subs.add_parser("list", help="Show the current target company list")

    # show
    p_show = subs.add_parser("show", help="Show details for one company")
    p_show.add_argument("name", help="Company name (substring match)")

    # add
    p_add = subs.add_parser("add", help="Manually add a company")
    p_add.add_argument("name", help="Company name")
    p_add.add_argument("--website", "-w", default="", help="Company website")
    p_add.add_argument("--github", "-g", help="GitHub org name")
    p_add.add_argument("--description", "-d", default="", help="What they do")
    p_add.add_argument("--region", "-r", default="", help="Region (Gulf/Africa/India/Europe/US)")

    # remove
    p_rm = subs.add_parser("remove", help="Remove a company from the list")
    p_rm.add_argument("name", help="Company name (substring match)")

    # source
    p_src = subs.add_parser("source", help="Find people at a company for a role")
    p_src.add_argument("name", help="Company name (substring match)")
    p_src.add_argument("--role", "-r", required=True,
                       help="Role type (sales/marketing/partnerships/customer_success/etc)")
    p_src.add_argument("--no-enrich", action="store_true")
    p_src.add_argument("--enrich-limit", type=int, default=10)

    # source-all
    p_srcall = subs.add_parser("source-all", help="Find people at ALL target companies for a role")
    p_srcall.add_argument("--role", "-r", required=True,
                          help="Role type (sales/marketing/partnerships/customer_success/etc)")
    p_srcall.add_argument("--no-enrich", action="store_true")
    p_srcall.add_argument("--enrich-limit", type=int, default=10)
    p_srcall.add_argument("--limit", "-n", type=int, help="Max companies to search")

    args = parser.parse_args()

    if args.command == "discover":
        print(f"Discovering target companies: '{args.query}'\n")
        new_companies = discover_companies(args.query)
        if not new_companies:
            print("  No companies found.")
            return

        # Merge into existing list
        existing = load_companies()
        existing_names = {c.name.lower() for c in existing}
        added = 0
        for c in new_companies:
            if c.name.lower() not in existing_names:
                existing.append(c)
                existing_names.add(c.name.lower())
                added += 1
        save_companies(existing)
        print(f"\n  Added {added} new companies ({len(new_companies) - added} already in list)")
        print(f"  Total: {len(existing)} target companies")
        print(_render_company_table(existing))

    elif args.command == "list":
        companies = load_companies()
        if not companies:
            print("  No target companies. Run: python companies.py discover \"your query\"")
        else:
            print(_render_company_table(companies))

    elif args.command == "show":
        company = find_company_by_name(args.name)
        if not company:
            print(f"  No company matching '{args.name}'")
        else:
            print(_render_company_detail(company))

    elif args.command == "add":
        company = CompanyProfile(
            name=args.name,
            website=args.website,
            github_org=args.github,
            description=args.description,
            region=args.region,
        )
        companies = add_company(company)
        print(f"  Added {args.name} ({len(companies)} total)")

    elif args.command == "remove":
        before = len(load_companies())
        companies = remove_company(args.name)
        removed = before - len(companies)
        if removed:
            print(f"  Removed {removed} company matching '{args.name}' ({len(companies)} remaining)")
        else:
            print(f"  No company matching '{args.name}'")

    elif args.command == "source":
        company = find_company_by_name(args.name)
        if not company:
            print(f"  No company matching '{args.name}'")
            return
        candidates = find_people_by_role(company, args.role)
        candidates = deduplicate(candidates)
        if not candidates:
            print(f"  No {args.role} candidates found at {company.name}")
            return
        from output.terminal import render_candidate_table
        print(render_candidate_table(candidates))
        if not args.no_enrich:
            from cli_common import enrich_candidate
            from output.store import save_dossier
            _enrich_candidates(candidates, args, company.name)

    elif args.command == "source-all":
        companies = load_companies()
        if not companies:
            print("  No target companies. Run: python companies.py discover \"your query\"")
            return
        if args.limit:
            companies = companies[:args.limit]
        all_candidates = []
        for company in companies:
            candidates = find_people_by_role(company, args.role)
            all_candidates.extend(candidates)
        all_candidates = deduplicate(all_candidates)
        print(f"\n  Total: {len(all_candidates)} {args.role} candidates "
              f"from {len(companies)} companies")
        from output.terminal import render_candidate_table
        print(render_candidate_table(all_candidates))
        if not args.no_enrich:
            _enrich_candidates(all_candidates, args, "all companies")


def _enrich_candidates(candidates, args, source_label):
    """Enrich and save candidates, then generate PDF."""
    from cli_common import enrich_candidate
    from output.store import save_dossier

    to_enrich = candidates[:args.enrich_limit]
    print(f"\n--- Enriching {len(to_enrich)} candidates from {source_label} ---")
    dossiers = []
    for i, candidate in enumerate(to_enrich, 1):
        print(f"\n[{i}/{len(to_enrich)}] {candidate.keys.strongest_key()}")
        dossier = enrich_candidate(candidate, role_context=args.role)
        save_dossier(dossier)
        dossiers.append(dossier)
        print(f"  -> confidence: {dossier.profile.confidence:.0%}")

    dossiers.sort(key=lambda d: d.rank_score, reverse=True)
    print(f"\n=== {len(dossiers)} candidates enriched ===")

    from output.pdf import generate_pdf
    pdf_path = generate_pdf(dossiers)
    print(f"\n  PDF generated: {pdf_path}")
    import subprocess
    subprocess.run(["open", "-a", "Skim", str(pdf_path)])


if __name__ == "__main__":
    main()
