#!/usr/bin/env python3
"""Stage85 — live coverage audit for Team Style Dimensions.

This module answers a different question from the Stage85 readiness checker:

Readiness:
    Does the architecture support the metrics needed by a dimension?

Coverage:
    Do real Stage84 observations currently contain enough known components
    for individual team profiles to be eligible for later validation?

This module does NOT decide that the historical validation sample is sufficient.
It does NOT create style scores or arbitrary dimension weights.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SPEC_PATH = ROOT / "config" / "pbk_team_style_dimensions_v1.json"
DEFAULT_OBSERVATIONS_PATH = (
    ROOT / "ops" / "team_style_metric_observations.jsonl"
)

VERSION = "PBK_STAGE85_TEAM_STYLE_DIMENSIONS_COVERAGE_V1"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")

    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()

            if not text:
                continue

            payload = json.loads(text)

            if not isinstance(payload, dict):
                raise ValueError(
                    f"{path}:{line_number}: JSONL row must be an object"
                )

            rows.append(payload)

    return rows


def dimension_components(
    dimension: dict[str, Any],
) -> list[str]:
    components = dimension.get("components")

    if not isinstance(components, list):
        return []

    result: list[str] = []

    for component in components:
        if not isinstance(component, dict):
            continue

        metric = str(component.get("metric") or "").strip()

        if metric:
            result.append(metric)

    return result


def profile_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("league_id") or ""),
        str(row.get("season") or ""),
        str(row.get("team_id") or ""),
        str(row.get("split") or "").lower(),
        str(row.get("window") or ""),
        str(
            row.get("profile_before_utc")
            or row.get("observed_at_utc")
            or ""
        ),
    )


def row_has_known_value(row: dict[str, Any]) -> bool:
    metric_status = str(
        row.get("metric_status") or ""
    ).strip().upper()

    value = row.get("value")

    return metric_status == "KNOWN" and value is not None


def group_profile_metrics(
    rows: Iterable[dict[str, Any]],
) -> dict[tuple[str, ...], set[str]]:
    grouped: dict[tuple[str, ...], set[str]] = defaultdict(set)

    for row in rows:
        if not isinstance(row, dict):
            continue

        metric = str(row.get("metric") or "").strip()

        if not metric:
            continue

        key = profile_key(row)

        if not all(key):
            continue

        if row_has_known_value(row):
            grouped[key].add(metric)

        else:
            # Preserve profile existence even when this metric is UNKNOWN.
            grouped[key]

    return dict(grouped)


def assess_dimension_coverage(
    dimension: dict[str, Any],
    grouped_profiles: dict[tuple[str, ...], set[str]],
) -> dict[str, Any]:
    dimension_id = str(dimension.get("id") or "").strip()

    if not dimension_id:
        raise ValueError("dimension id is required")

    declared_status = str(
        dimension.get("status") or ""
    ).strip()

    components = dimension_components(dimension)

    minimum_known_components = dimension.get(
        "minimum_known_components",
        len(components),
    )

    try:
        minimum_known_components = int(minimum_known_components)
    except (TypeError, ValueError):
        raise ValueError(
            f"{dimension_id}: minimum_known_components must be an integer"
        )

    total_profiles = len(grouped_profiles)

    if declared_status == "DATA_BLOCKED":
        return {
            "dimension": dimension_id,
            "declared_status": declared_status,
            "coverage_state": "DATA_BLOCKED",
            "components": components,
            "minimum_known_components": minimum_known_components,
            "total_profiles": total_profiles,
            "eligible_profiles": 0,
            "eligible_ratio": None,
            "validation_sample_ready": False,
            "style_score_created": False,
            "arbitrary_weights_used": False,
        }

    if declared_status == "RESEARCH_CONTEXT_ONLY":
        return {
            "dimension": dimension_id,
            "declared_status": declared_status,
            "coverage_state": "CONTEXT_ONLY",
            "components": components,
            "minimum_known_components": minimum_known_components,
            "total_profiles": total_profiles,
            "eligible_profiles": 0,
            "eligible_ratio": None,
            "validation_sample_ready": False,
            "style_score_created": False,
            "arbitrary_weights_used": False,
        }

    if not components:
        coverage_state = "NO_COMPONENT_DEFINITION"
        eligible_profiles = 0

    else:
        eligible_profiles = 0
        component_set = set(components)

        for known_metrics in grouped_profiles.values():
            known_count = len(
                component_set.intersection(known_metrics)
            )

            if known_count >= minimum_known_components:
                eligible_profiles += 1

        if total_profiles == 0:
            coverage_state = "WAITING_FOR_LIVE_COVERAGE"
        elif eligible_profiles == 0:
            coverage_state = "NO_ELIGIBLE_PROFILES"
        else:
            coverage_state = "LIVE_COVERAGE_PRESENT"

    eligible_ratio = (
        round(eligible_profiles / total_profiles, 6)
        if total_profiles > 0
        else None
    )

    return {
        "dimension": dimension_id,
        "declared_status": declared_status,
        "coverage_state": coverage_state,
        "components": components,
        "minimum_known_components": minimum_known_components,
        "total_profiles": total_profiles,
        "eligible_profiles": eligible_profiles,
        "eligible_ratio": eligible_ratio,
        "validation_sample_ready": False,
        "validation_sample_policy_locked": False,
        "style_score_created": False,
        "arbitrary_weights_used": False,
    }


def build_coverage_report(
    spec: dict[str, Any],
    observations: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    dimensions = spec.get("dimensions")

    if not isinstance(dimensions, list):
        raise ValueError("spec dimensions must be a list")

    rows = [
        row
        for row in observations
        if isinstance(row, dict)
    ]

    grouped_profiles = group_profile_metrics(rows)

    assessments = [
        assess_dimension_coverage(
            dimension,
            grouped_profiles,
        )
        for dimension in dimensions
        if isinstance(dimension, dict)
    ]

    return {
        "version": VERSION,
        "spec_version": spec.get("version"),
        "stage": 85,
        "status": (
            "WAITING_FOR_STAGE84_OBSERVATIONS"
            if not rows
            else "LIVE_COVERAGE_AUDIT"
        ),
        "observation_rows": len(rows),
        "distinct_profiles": len(grouped_profiles),
        "dimensions": assessments,
        "validation_sample_policy_locked": False,
        "provider_calls_added": 0,
        "research_only": True,
        "missing_evidence_policy": "UNKNOWN_NOT_ZERO",
        "arbitrary_weights_allowed": False,
        "style_score_created": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "creates_signal": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "r1_r2_r3_mutation": False,
        "ui_changes": False,
        "api_changes": False,
    }


def main() -> int:
    spec = load_json(DEFAULT_SPEC_PATH)
    observations = read_jsonl(DEFAULT_OBSERVATIONS_PATH)

    report = build_coverage_report(
        spec,
        observations,
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())