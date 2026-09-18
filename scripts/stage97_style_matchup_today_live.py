#!/usr/bin/env python3
"""Stage97 — Style/Matchup Today/LIVE read model."""

from __future__ import annotations

from typing import Any

try:
    from style_matchup_passport import build_style_matchup_passport
except ModuleNotFoundError:
    from scripts.style_matchup_passport import build_style_matchup_passport


VERSION = "PBK_STAGE97_STYLE_MATCHUP_TODAY_LIVE_V1"


def build_today_live_style_context(
    conn,
    fixture: dict[str, Any],
) -> dict[str, Any]:
    context = build_style_matchup_passport(
        conn,
        fixture,
    )

    style = context.get("style_validation") or {}
    matchup = context.get("matchup_validation") or {}

    return {
        "version": VERSION,
        "fixture_id": str(
            fixture.get("fixture_id") or ""
        ),
        "available": bool(
            context.get("available")
        ),
        "style_status": (
            style.get("status")
            or "DATA_WAITING"
        ),
        "ready_dimensions": (
            style.get("ready_dimensions")
            or []
        ),
        "validation_evidence_dimensions": (
            style.get(
                "validation_evidence_dimensions"
            )
            or []
        ),
        "matchup_status": (
            matchup.get("status")
            or "DATA_WAITING"
        ),
        "components_with_required_evidence": (
            matchup.get(
                "components_with_required_evidence"
            )
            or 0
        ),
        "total_matchup_components": (
            matchup.get("total_components")
            or 0
        ),
        "validated_style_claim_allowed": False,
        "validated_matchup_claim_allowed": False,
        "matchup_grade_authorized": False,
        "overall_edge_authorized": False,
        "research_only": True,
        "no_lookahead": True,
        "provider_polling": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }
