#!/usr/bin/env python3
"""PBK style-vs-style matchup research foundation.

This module is deliberately research-only. It represents explicit pre-kickoff
team-style evidence and directional matchup components without inventing a
single Matchup Grade, causal effect, betting signal, probability adjustment or
stake rule.

Important governance rules:
- formation alone is context, not a team style;
- missing style evidence remains UNKNOWN and is never filled with zero;
- every usable style dimension requires source + aware observed_at_utc;
- evidence observed after the target kickoff/cutoff is excluded;
- directional components remain independent until separately validated.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

STYLE_DIMENSIONS = (
    "PRESS_INTENSITY",
    "BUILDUP_RESISTANCE",
    "TRANSITION_ATTACK",
    "TRANSITION_DEFENCE",
    "WIDTH_ATTACK",
    "WIDE_DEFENCE",
    "AERIAL_ATTACK",
    "AERIAL_DEFENCE",
    "SET_PIECE_ATTACK",
    "SET_PIECE_DEFENCE",
    "LOW_BLOCK_BREAKING",
    "LOW_BLOCK_DEFENCE",
    "CENTRAL_PROGRESSION",
    "CENTRAL_COMPACTNESS",
)

# Each component is directional: the first dimension belongs to the acting team
# and the second belongs to the opponent. Delta is descriptive only.
MATCHUP_COMPONENTS = {
    "PRESS_VS_BUILDUP": ("PRESS_INTENSITY", "BUILDUP_RESISTANCE"),
    "TRANSITION_VS_TRANSITION_DEFENCE": ("TRANSITION_ATTACK", "TRANSITION_DEFENCE"),
    "WIDTH_VS_WIDE_DEFENCE": ("WIDTH_ATTACK", "WIDE_DEFENCE"),
    "AERIAL_VS_AERIAL_DEFENCE": ("AERIAL_ATTACK", "AERIAL_DEFENCE"),
    "SET_PIECE_VS_SET_PIECE_DEFENCE": ("SET_PIECE_ATTACK", "SET_PIECE_DEFENCE"),
    "LOW_BLOCK_BREAKING_VS_LOW_BLOCK_DEFENCE": ("LOW_BLOCK_BREAKING", "LOW_BLOCK_DEFENCE"),
    "CENTRAL_PROGRESSION_VS_CENTRAL_COMPACTNESS": ("CENTRAL_PROGRESSION", "CENTRAL_COMPACTNESS"),
}


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def fnum(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _unknown(reason: str) -> dict[str, Any]:
    return {
        "status": "UNKNOWN",
        "value": None,
        "source": None,
        "observed_at_utc": None,
        "sample_size": None,
        "confidence": "UNKNOWN",
        "limitations": [reason],
    }


def normalize_style_vector(
    evidence: dict[str, dict[str, Any]] | None,
    before_utc: str,
) -> dict[str, Any]:
    """Normalize explicit style evidence known by `before_utc`.

    Values are descriptive 0..10 research scales supplied by upstream feature
    producers. This function does not derive them from formation names and does
    not infer any missing dimension.
    """
    cutoff = parse_iso(before_utc)
    if cutoff is None:
        raise ValueError("aware before_utc is required")

    evidence = evidence or {}
    unsupported = sorted(set(evidence) - set(STYLE_DIMENSIONS))
    if unsupported:
        raise ValueError(f"unsupported style dimensions: {', '.join(unsupported)}")

    dimensions: dict[str, dict[str, Any]] = {}
    known = 0
    for dimension in STYLE_DIMENSIONS:
        row = dict(evidence.get(dimension) or {})
        if not row:
            dimensions[dimension] = _unknown("MISSING_EVIDENCE")
            continue

        source = str(row.get("source") or "").strip()
        observed = parse_iso(row.get("observed_at_utc"))
        value = fnum(row.get("value"))
        if not source:
            dimensions[dimension] = _unknown("SOURCE_REQUIRED")
            continue
        if observed is None:
            dimensions[dimension] = _unknown("AWARE_OBSERVED_AT_REQUIRED")
            continue
        if observed > cutoff:
            dimensions[dimension] = _unknown("EVIDENCE_AFTER_CUTOFF")
            continue
        if value is None:
            dimensions[dimension] = _unknown("NUMERIC_VALUE_REQUIRED")
            continue
        if not 0.0 <= value <= 10.0:
            raise ValueError(f"{dimension}: value must be within 0..10")

        sample_size = row.get("sample_size")
        if sample_size is not None:
            try:
                sample_size = int(sample_size)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{dimension}: sample_size must be an integer") from exc
            if sample_size < 0:
                raise ValueError(f"{dimension}: sample_size must be >= 0")

        limitations = list(row.get("limitations") or [])
        dimensions[dimension] = {
            "status": "KNOWN",
            "value": round(value, 3),
            "source": source,
            "observed_at_utc": observed.isoformat(),
            "sample_size": sample_size,
            "confidence": str(row.get("confidence") or "UNKNOWN").upper(),
            "limitations": limitations,
        }
        known += 1

    return {
        "version": "PBK_STYLE_VECTOR_V1",
        "before_utc": before_utc,
        "dimensions": dimensions,
        "known_dimensions": known,
        "total_dimensions": len(STYLE_DIMENSIONS),
        "coverage_pct": round(100.0 * known / len(STYLE_DIMENSIONS), 2),
        "formation_is_style": False,
        "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def directed_matchup(
    acting_style: dict[str, dict[str, Any]] | None,
    opponent_style: dict[str, dict[str, Any]] | None,
    before_utc: str,
    *,
    formation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build independent directional matchup components.

    `delta = acting value - opponent defensive/resistance value` is exposed as a
    transparent descriptive component. It is not an edge, grade or probability
    adjustment and receives no hand-written weight.
    """
    acting = normalize_style_vector(acting_style, before_utc)
    opponent = normalize_style_vector(opponent_style, before_utc)
    components: dict[str, Any] = {}
    known = 0

    for component, (acting_dim, opponent_dim) in MATCHUP_COMPONENTS.items():
        left = acting["dimensions"][acting_dim]
        right = opponent["dimensions"][opponent_dim]
        if left["status"] != "KNOWN" or right["status"] != "KNOWN":
            reasons = []
            if left["status"] != "KNOWN":
                reasons.append(f"ACTING_{acting_dim}_UNKNOWN")
            if right["status"] != "KNOWN":
                reasons.append(f"OPPONENT_{opponent_dim}_UNKNOWN")
            components[component] = {
                "status": "UNKNOWN",
                "acting_dimension": acting_dim,
                "opponent_dimension": opponent_dim,
                "acting_value": left.get("value"),
                "opponent_value": right.get("value"),
                "delta": None,
                "limitations": reasons,
            }
            continue

        delta = round(float(left["value"]) - float(right["value"]), 3)
        components[component] = {
            "status": "KNOWN",
            "acting_dimension": acting_dim,
            "opponent_dimension": opponent_dim,
            "acting_value": left["value"],
            "opponent_value": right["value"],
            "delta": delta,
            "acting_source": left["source"],
            "opponent_source": right["source"],
            "limitations": ["DESCRIPTIVE_DELTA_ONLY", "NO_CAUSAL_CLAIM"],
        }
        known += 1

    formation_context = dict(formation_context or {})
    return {
        "version": "PBK_DIRECTED_MATCHUP_V1",
        "before_utc": before_utc,
        "components": components,
        "known_components": known,
        "total_components": len(MATCHUP_COMPONENTS),
        "coverage_pct": round(100.0 * known / len(MATCHUP_COMPONENTS), 2),
        "formation_context": formation_context,
        "formation_used_as_style_feature": False,
        "matchup_grade": None,
        "overall_edge": None,
        "component_weights": None,
        "aggregation_status": "NOT_AUTHORIZED_UNTIL_OOS_VALIDATION",
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "ui_changes": False,
    }


def matchup_report(
    home_style: dict[str, dict[str, Any]] | None,
    away_style: dict[str, dict[str, Any]] | None,
    before_utc: str,
    *,
    home_formation: str | None = None,
    away_formation: str | None = None,
) -> dict[str, Any]:
    """Return both directions without selecting a winner or combined score."""
    formation_context = {
        "home_formation": home_formation,
        "away_formation": away_formation,
        "purpose": "CONTEXT_ONLY",
    }
    return {
        "version": "PBK_MATCHUP_REPORT_V1",
        "before_utc": before_utc,
        "home_vs_away": directed_matchup(
            home_style,
            away_style,
            before_utc,
            formation_context=formation_context,
        ),
        "away_vs_home": directed_matchup(
            away_style,
            home_style,
            before_utc,
            formation_context=formation_context,
        ),
        "matchup_grade": None,
        "winner": None,
        "component_weighting": None,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "ui_changes": False,
    }
