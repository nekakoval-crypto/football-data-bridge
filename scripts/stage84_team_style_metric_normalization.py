#!/usr/bin/env python3
"""Stage84 — empirical normalization for Team Style raw metrics.

This stage is provider-free and research-only.

It normalizes individual raw Team Style metrics against a comparable
historical population using empirical percentile and z-score.

It does NOT:
- create 0..10 style dimensions
- create Matchup Grade
- create betting signals
- mutate probability/value/EV/stake
- mutate R1/R2/R3
- mutate Forward Journal
- mutate UI/API
- silently broaden population scope
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

MIN_POPULATION = 30
VERSION = "PBK_STAGE84_TEAM_STYLE_METRIC_NORMALIZATION_V1"


@dataclass(frozen=True)
class PopulationKey:
    league_id: str
    season: str
    split: str
    window: int
    metric: str


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


def empirical_percentile(values: list[float], target: float) -> float:
    """Mid-rank empirical percentile in range 0..100."""
    if not values:
        raise ValueError("values required")

    below = sum(1 for value in values if value < target)
    equal = sum(1 for value in values if value == target)

    percentile = 100.0 * (below + 0.5 * equal) / len(values)
    return round(percentile, 4)


def z_score(values: list[float], target: float) -> float | None:
    if len(values) < 2:
        return None

    mean = statistics.mean(values)
    std = statistics.stdev(values)

    if std == 0:
        return 0.0 if target == mean else None

    return round((target - mean) / std, 6)


def normalize_metric(
    *,
    raw_value: Any,
    population_values: Iterable[Any],
    min_population: int = MIN_POPULATION,
) -> dict[str, Any]:
    if min_population <= 0:
        raise ValueError("min_population must be positive")

    target = fnum(raw_value)
    if target is None:
        return {
            "status": "UNKNOWN_RAW_VALUE",
            "raw_value": None,
            "population_n": 0,
            "population_mean": None,
            "population_std": None,
            "percentile": None,
            "z_score": None,
            "style_dimension_value": None,
        }

    values = [
        number
        for number in (fnum(value) for value in population_values)
        if number is not None
    ]

    if len(values) < min_population:
        return {
            "status": "INSUFFICIENT_POPULATION",
            "raw_value": target,
            "population_n": len(values),
            "population_mean": round(statistics.mean(values), 6) if values else None,
            "population_std": (
                round(statistics.stdev(values), 6)
                if len(values) >= 2
                else None
            ),
            "percentile": None,
            "z_score": None,
            "style_dimension_value": None,
        }

    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) >= 2 else 0.0

    return {
        "status": "NORMALIZED",
        "raw_value": target,
        "population_n": len(values),
        "population_mean": round(mean, 6),
        "population_std": round(std, 6),
        "percentile": empirical_percentile(values, target),
        "z_score": z_score(values, target),
        "style_dimension_value": None,
    }


def validate_population_scope(
    row: dict[str, Any],
    *,
    before_utc: str,
) -> tuple[bool, str | None]:
    cutoff = parse_iso(before_utc)
    if cutoff is None:
        raise ValueError("aware before_utc is required")

    observed = parse_iso(row.get("observed_at_utc"))
    if observed is None:
        return False, "MISSING_OR_NAIVE_OBSERVED_AT"

    if observed > cutoff:
        return False, "OBSERVED_AFTER_CUTOFF"

    profile_cutoff = parse_iso(row.get("profile_before_utc"))
    if profile_cutoff is None:
        return False, "MISSING_OR_NAIVE_PROFILE_CUTOFF"

    if profile_cutoff > cutoff:
        return False, "PROFILE_AFTER_CUTOFF"

    return True, None


def build_population(
    rows: Iterable[dict[str, Any]],
    *,
    key: PopulationKey,
    before_utc: str,
) -> tuple[list[float], dict[str, int]]:
    values: list[float] = []

    exclusions = {
        "wrong_league": 0,
        "wrong_season": 0,
        "wrong_split": 0,
        "wrong_window": 0,
        "wrong_metric": 0,
        "invalid_time_scope": 0,
        "missing_value": 0,
    }

    for row in rows:
        row = dict(row or {})

        if str(row.get("league_id") or "") != key.league_id:
            exclusions["wrong_league"] += 1
            continue

        if str(row.get("season") or "") != key.season:
            exclusions["wrong_season"] += 1
            continue

        if str(row.get("split") or "").lower() != key.split.lower():
            exclusions["wrong_split"] += 1
            continue

        try:
            window = int(row.get("window"))
        except (TypeError, ValueError):
            exclusions["wrong_window"] += 1
            continue

        if window != key.window:
            exclusions["wrong_window"] += 1
            continue

        if str(row.get("metric") or "") != key.metric:
            exclusions["wrong_metric"] += 1
            continue

        valid, _reason = validate_population_scope(
            row,
            before_utc=before_utc,
        )
        if not valid:
            exclusions["invalid_time_scope"] += 1
            continue

        value = fnum(row.get("value"))
        if value is None:
            exclusions["missing_value"] += 1
            continue

        values.append(value)

    return values, exclusions


def normalize_against_population(
    *,
    target_row: dict[str, Any],
    population_rows: Iterable[dict[str, Any]],
    before_utc: str,
    min_population: int = MIN_POPULATION,
) -> dict[str, Any]:
    key = PopulationKey(
        league_id=str(target_row.get("league_id") or ""),
        season=str(target_row.get("season") or ""),
        split=str(target_row.get("split") or "").lower(),
        window=int(target_row.get("window")),
        metric=str(target_row.get("metric") or ""),
    )

    if not all(
        [
            key.league_id,
            key.season,
            key.split,
            key.metric,
            key.window > 0,
        ]
    ):
        raise ValueError("complete population key is required")

    valid_target, target_reason = validate_population_scope(
        target_row,
        before_utc=before_utc,
    )

    if not valid_target:
        return {
            "version": VERSION,
            "status": "INVALID_TARGET_SCOPE",
            "reason": target_reason,
            "population_key": {
                "league_id": key.league_id,
                "season": key.season,
                "split": key.split,
                "window": key.window,
                "metric": key.metric,
            },
            "normalized": None,
            "provider_calls_added": 0,
            "research_only": True,
            "style_dimension_value": None,
            "creates_signal": False,
            "probability_mutation": False,
            "eligibility_mutation": False,
            "stake_changes": False,
            "forward_journal_mutation": False,
            "r1_r2_r3_mutation": False,
            "ui_changes": False,
            "api_changes": False,
        }

    population, exclusions = build_population(
        population_rows,
        key=key,
        before_utc=before_utc,
    )

    normalized = normalize_metric(
        raw_value=target_row.get("value"),
        population_values=population,
        min_population=min_population,
    )

    return {
        "version": VERSION,
        "status": normalized["status"],
        "population_key": {
            "league_id": key.league_id,
            "season": key.season,
            "split": key.split,
            "window": key.window,
            "metric": key.metric,
        },
        "before_utc": before_utc,
        "normalized": normalized,
        "population_exclusions": exclusions,
        "min_population_policy": {
            "minimum": min_population,
            "status": "CALIBRATION_MIN_SAMPLE_POLICY",
            "validated_performance_threshold": False,
        },
        "provider_calls_added": 0,
        "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
        "silent_scope_broadening": False,
        "style_dimension_value": None,
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "r1_r2_r3_mutation": False,
        "ui_changes": False,
        "api_changes": False,
    }
