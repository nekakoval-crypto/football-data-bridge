#!/usr/bin/env python3
"""PBK rolling Team Style Profile research foundation.

The engine is provider-free and no-lookahead. It aggregates explicit match-level
team evidence into rolling 5/10/20-match profiles for overall/home/away splits.
It deliberately exposes raw descriptive metrics only. It does not invent a
0..10 team-style score, Matchup Grade, probability adjustment, betting signal
or stake rule.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime
from typing import Any, Iterable

DEFAULT_WINDOWS = (5, 10, 20)
SPLITS = ("overall", "home", "away")

RAW_METRICS = (
    "shots_for",
    "shots_against",
    "shots_on_target_for",
    "shots_on_target_against",
    "xg_for",
    "xg_against",
    "possession_pct",
    "corners_for",
    "corners_against",
    "passes",
    "pass_accuracy_pct",
    "long_ball_share_pct",
    "ppda",
    "high_turnovers",
    "crosses",
    "aerial_duel_win_pct",
    "set_piece_xg_for",
    "set_piece_xg_against",
    "progressive_passes",
    "progressive_carries",
    "field_tilt_pct",
    "transition_shots_for",
    "transition_shots_against",
)

# These are candidate raw inputs for later matchup calibration. Presence of a
# raw input does not authorize a 0..10 style dimension or any directional edge.
MATCHUP_DIMENSION_CANDIDATES = {
    "PRESS_INTENSITY": ("ppda", "high_turnovers"),
    "BUILDUP_RESISTANCE": ("pass_accuracy_pct", "possession_pct"),
    "TRANSITION_ATTACK": ("transition_shots_for",),
    "TRANSITION_DEFENCE": ("transition_shots_against",),
    "WIDTH_ATTACK": ("crosses", "corners_for"),
    "WIDE_DEFENCE": ("corners_against",),
    "AERIAL_ATTACK": ("aerial_duel_win_pct",),
    "AERIAL_DEFENCE": ("aerial_duel_win_pct",),
    "SET_PIECE_ATTACK": ("set_piece_xg_for", "corners_for"),
    "SET_PIECE_DEFENCE": ("set_piece_xg_against", "corners_against"),
    "LOW_BLOCK_BREAKING": ("field_tilt_pct", "progressive_passes", "progressive_carries"),
    "LOW_BLOCK_DEFENCE": ("field_tilt_pct", "xg_against"),
    "CENTRAL_PROGRESSION": ("progressive_passes", "progressive_carries"),
    "CENTRAL_COMPACTNESS": ("xg_against", "shots_against"),
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


def _metric_value(row: dict[str, Any], metric: str) -> float | None:
    nested = row.get("metrics")
    if isinstance(nested, dict) and metric in nested:
        return fnum(nested.get(metric))
    return fnum(row.get(metric))


def _normalize_venue(value: Any) -> str | None:
    venue = str(value or "").strip().upper()
    if venue in {"H", "HOME"}:
        return "home"
    if venue in {"A", "AWAY"}:
        return "away"
    return None


def _prepare_rows(match_rows: Iterable[dict[str, Any]], before_utc: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    cutoff = parse_iso(before_utc)
    if cutoff is None:
        raise ValueError("aware before_utc is required")

    accepted: list[dict[str, Any]] = []
    exclusions = {
        "missing_source": 0,
        "missing_or_naive_observed_at": 0,
        "observed_after_cutoff": 0,
        "missing_or_naive_kickoff": 0,
        "kickoff_not_before_cutoff": 0,
        "unknown_venue": 0,
    }

    for original in match_rows:
        row = dict(original or {})
        source = str(row.get("source") or "").strip()
        if not source:
            exclusions["missing_source"] += 1
            continue
        observed = parse_iso(row.get("observed_at_utc"))
        if observed is None:
            exclusions["missing_or_naive_observed_at"] += 1
            continue
        if observed > cutoff:
            exclusions["observed_after_cutoff"] += 1
            continue
        kickoff = parse_iso(row.get("kickoff_utc"))
        if kickoff is None:
            exclusions["missing_or_naive_kickoff"] += 1
            continue
        if kickoff >= cutoff:
            exclusions["kickoff_not_before_cutoff"] += 1
            continue
        venue = _normalize_venue(row.get("venue"))
        if venue is None:
            exclusions["unknown_venue"] += 1
            continue

        row["source"] = source
        row["_observed"] = observed
        row["_kickoff"] = kickoff
        row["_venue"] = venue
        accepted.append(row)

    accepted.sort(key=lambda row: row["_kickoff"], reverse=True)
    return accepted, exclusions


def _aggregate_metric(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    values: list[float] = []
    sources: set[str] = set()
    observed_values: list[datetime] = []
    for row in rows:
        value = _metric_value(row, metric)
        if value is None:
            continue
        values.append(value)
        sources.add(str(row["source"]))
        observed_values.append(row["_observed"])

    total = len(rows)
    if not values:
        return {
            "status": "UNKNOWN",
            "mean": None,
            "median": None,
            "sample_size": 0,
            "window_matches": total,
            "coverage_pct": 0.0,
            "sources": [],
            "latest_observed_at_utc": None,
            "style_scale_value": None,
            "limitations": ["NO_OBSERVED_VALUES", "NOT_ZERO_FILLED", "NO_STYLE_CALIBRATION"],
        }

    return {
        "status": "KNOWN",
        "mean": round(sum(values) / len(values), 4),
        "median": round(statistics.median(values), 4),
        "sample_size": len(values),
        "window_matches": total,
        "coverage_pct": round(100.0 * len(values) / total, 2) if total else 0.0,
        "sources": sorted(sources),
        "latest_observed_at_utc": max(observed_values).isoformat(),
        "style_scale_value": None,
        "limitations": ["RAW_DESCRIPTIVE_COMPONENT", "NO_STYLE_CALIBRATION"],
    }


def _dimension_candidates(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for dimension, candidate_metrics in MATCHUP_DIMENSION_CANDIDATES.items():
        available = [name for name in candidate_metrics if metrics.get(name, {}).get("status") == "KNOWN"]
        output[dimension] = {
            "status": "RAW_INPUT_AVAILABLE_REQUIRES_CALIBRATION" if available else "UNKNOWN",
            "available_raw_metrics": available,
            "candidate_raw_metrics": list(candidate_metrics),
            "value": None,
            "calibration_status": "NOT_VALIDATED",
        }
    return output


def _window_profile(rows: list[dict[str, Any]], requested_window: int) -> dict[str, Any]:
    selected = rows[:requested_window]
    metrics = {metric: _aggregate_metric(selected, metric) for metric in RAW_METRICS}
    formations = [str(row.get("formation") or "").strip() for row in selected]
    formations = [value for value in formations if value]
    return {
        "requested_window": requested_window,
        "actual_matches": len(selected),
        "window_complete": len(selected) >= requested_window,
        "fixture_ids": [row.get("fixture_id") for row in selected if row.get("fixture_id") is not None],
        "oldest_kickoff_utc": selected[-1]["_kickoff"].isoformat() if selected else None,
        "newest_kickoff_utc": selected[0]["_kickoff"].isoformat() if selected else None,
        "metrics": metrics,
        "matchup_dimension_candidates": _dimension_candidates(metrics),
        "formation_context": {
            "observed_formations": formations,
            "used_as_style_feature": False,
            "purpose": "CONTEXT_ONLY",
        },
        "overall_style_score": None,
        "component_weights": None,
        "aggregation_status": "NOT_AUTHORIZED_UNTIL_CALIBRATION_AND_OOS_VALIDATION",
    }


def build_team_style_profile(
    match_rows: Iterable[dict[str, Any]],
    before_utc: str,
    *,
    windows: Iterable[int] = DEFAULT_WINDOWS,
) -> dict[str, Any]:
    """Build rolling raw style profiles known before `before_utc`.

    Input rows must have source, observed_at_utc, kickoff_utc and venue. Metrics
    may be top-level fields or nested under ``metrics``. No provider calls are
    made and no missing metric is imputed.
    """
    normalized_windows = tuple(int(value) for value in windows)
    if not normalized_windows or any(value <= 0 for value in normalized_windows):
        raise ValueError("windows must contain positive integers")
    if len(set(normalized_windows)) != len(normalized_windows):
        raise ValueError("windows must be unique")

    prepared, exclusions = _prepare_rows(match_rows, before_utc)
    split_rows = {
        "overall": prepared,
        "home": [row for row in prepared if row["_venue"] == "home"],
        "away": [row for row in prepared if row["_venue"] == "away"],
    }

    profiles: dict[str, Any] = {}
    for split in SPLITS:
        rows = split_rows[split]
        profiles[split] = {
            "eligible_matches": len(rows),
            "windows": {str(window): _window_profile(rows, window) for window in normalized_windows},
        }

    return {
        "version": "PBK_TEAM_STYLE_PROFILE_V1",
        "before_utc": before_utc,
        "windows": list(normalized_windows),
        "splits": profiles,
        "eligible_matches_total": len(prepared),
        "exclusions": exclusions,
        "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
        "formation_is_style": False,
        "raw_components_only": True,
        "style_scale_calibrated": False,
        "provider_calls_added": 0,
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "ui_changes": False,
    }
