"""Human-readable terminal output for dossiers and candidates."""

from __future__ import annotations

from models import Candidate, Dossier


def render_candidate(candidate: Candidate, index: int) -> str:
    """Render a raw (un-enriched) candidate."""
    k = candidate.keys
    lines = [
        f"  {index:>3}  {k.name or '?':<30}  "
        f"{k.github_handle or '-':<20}  "
        f"score: {candidate.breakout_score:.2f}  "
        f"[{candidate.source_channel}]",
    ]
    if candidate.source_url:
        lines.append(f"       {candidate.source_url}")
    return "\n".join(lines)


def render_candidate_table(candidates: list[Candidate]) -> str:
    """Render a table of raw candidates."""
    header = f"  {'#':>3}  {'Name':<30}  {'GitHub':<20}  {'Score':>8}  Source"
    sep = "  " + "-" * 90
    rows = [header, sep]
    for i, c in enumerate(candidates, 1):
        rows.append(render_candidate(c, i))
    rows.append(sep)
    rows.append(f"  {len(candidates)} candidates found")
    return "\n".join(rows)


def render_dossier(dossier: Dossier) -> str:
    """Render a full enriched dossier card."""
    k = dossier.keys
    p = dossier.profile
    v = dossier.verification

    conf_bar = _confidence_bar(p.confidence)
    lines = [
        "",
        "=" * 60,
        f"  {p.name or k.name or '?'}",
        f"  confidence: {conf_bar} {p.confidence:.0%}"
        f"   rank: {dossier.rank_score:.2f}",
        "=" * 60,
    ]

    if p.location:
        lines.append(f"  Location:  {p.location}")
    if p.roles:
        lines.append(f"  Roles:     {', '.join(p.roles)}")
    if k.github_handle:
        lines.append(f"  GitHub:    github.com/{k.github_handle}")

    if p.summary:
        lines.append("")
        for line in _wrap(p.summary, 56):
            lines.append(f"  {line}")

    if dossier.sources:
        lines.append("")
        lines.append("  Sources:")
        for src in dossier.sources:
            lines.append(f"    - {src}")

    if p.links:
        lines.append("")
        lines.append("  Links:")
        for label, url in p.links.items():
            lines.append(f"    {label}: {url}")

    if p.gaps:
        lines.append("")
        lines.append("  Gaps:")
        for gap in p.gaps:
            lines.append(f"    - {gap}")

    refute_status = "CONFIRMED" if v.confirmed else "UNCONFIRMED"
    lines.append("")
    lines.append(f"  Refute:  {refute_status} (cap: {v.confidence_cap:.0%})")
    if v.refute_notes:
        for line in _wrap(v.refute_notes, 54):
            lines.append(f"    {line}")

    lines.append("-" * 60)
    return "\n".join(lines)


def render_dossier_table(dossiers: list[Dossier]) -> str:
    """Render a summary table of dossiers."""
    header = (
        f"  {'#':>3}  {'Conf':>6}  {'Rank':>6}  "
        f"{'Name':<25}  {'GitHub':<18}  Source"
    )
    sep = "  " + "-" * 90
    rows = [header, sep]
    for i, d in enumerate(dossiers, 1):
        name = (d.profile.name or d.keys.name or "?")[:25]
        gh = (d.keys.github_handle or "-")[:18]
        channels = ", ".join(d.source_channels) if d.source_channels else "-"
        rows.append(
            f"  {i:>3}  {d.profile.confidence:>5.0%}  "
            f"{d.rank_score:>6.2f}  {name:<25}  {gh:<18}  {channels}"
        )
    rows.append(sep)
    rows.append(f"  {len(dossiers)} dossiers")
    return "\n".join(rows)


def _confidence_bar(conf: float, width: int = 10) -> str:
    filled = int(conf * width)
    return "[" + "#" * filled + "." * (width - filled) + "]"


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines
