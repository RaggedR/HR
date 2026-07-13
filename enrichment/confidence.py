"""Confidence blending: merge research and refute signals."""

from __future__ import annotations

from models import Profile, Verification


def blend(profile: Profile, verification: Verification) -> float:
    """Compute final confidence. Refute can only lower, never raise."""
    final = min(profile.confidence, verification.confidence_cap)

    # Hard floor: unconfirmed identity caps at 0.4
    if not verification.confirmed:
        final = min(final, 0.4)

    # Fold refuted claims into gaps
    if verification.refute_notes and not verification.confirmed:
        profile.gaps.append(f"refute: {verification.refute_notes}")

    profile.confidence = final
    return final
