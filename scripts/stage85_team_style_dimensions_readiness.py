#!/usr/bin/env python3
"""Stage85 — readiness checker for Team Style Dimensions.

This script does not calculate style scores.

It compares the Stage85 dimension specification with the metrics that are
currently available from the Stage84 normalization layer and reports whether
each dimension is:

- READY_FOR_VALIDATION
- PARTIAL
- DATA_BLOCKED

No provider calls, probability changes, signals, stakes, R1/R2/R3 changes,
UI changes or API changes are allowed here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SPEC_PATH = ROOT / "config" / "pbk_team_style_dimensions_v1.json"

VERSION = "PBK_STAGE85_TEAM_STYLE_DIMENSIONS_READINESS_V1"


# Metrics which Stage82/83/84 can currently carry when source evidence exists.
CURRENT_STAGE84_METRICS = {
    "shots_for",
    "shots_against",
    "sot_for",
    "sot_against",
    "possession",
    "corners_for",
    "corners_against",
    "passes",
    "pass_accuracy",
    "xg_for",
    "xg_against",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")

    return payload


def available_metric_set(metrics: Iterable[str] | None = None) -> set[str]:
    source = CURRENT_STAGE84_METRICS if metrics is None else metrics

    return {
        str(metric).strip()
        for metric in source
        if str(metric).strip()
    }


def component_metrics(dimension: dict[str, Any]) -> list[str]:
    result: list[str] = []

    components = dimension.get("components")
    if not isinstance(components, list):
        return result

    for component in components:
        if not isinstance(component, dict):
            continue

        metric = str(component.get("metric") or "").strip()

        if metric:
            result.append(metric)

    return result


def required_future_metrics(dimension: dict[str, Any]) -> list[str]:
    payload = dimension.get("required_future_metrics")

    if not isinstance(payload, list):
        return []

    return [
        str(metric).strip()
        for metric in payload
        if str(metric).strip()
    ]


def assess_dimension(
    dimension: dict[str, Any],
    *,
    available_metrics: set[str],
) -> dict[str, Any]:
    dimension_id = str(dimension.get("id") or "").strip()

    if not dimension_id:
        raise ValueError("dimension id is required")

    declared_status = str(dimension.get("status") or "").strip()

    components = component_metrics(dimension)
    future_metrics = required_future_metrics(dimension)

    available_components = [
        metric for metric in components if metric in available_metrics
    ]

    missing_components = [
        metric for metric in components if metric not in available_metrics
    ]

    available_future_metrics = [
        metric for metric in future_metrics if metric in available_metrics
    ]

    missing_future_metrics = [
        metric for metric in future_metrics if metric not in available_metrics
    ]

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

    if minimum_known_components < 0:
        raise ValueError(
            f"{dimension_id}: minimum_known_components cannot be negative"
        )

    if declared_status == "DATA_BLOCKED":
        readiness = "DATA_BLOCKED"

    elif declared_status == "RESEARCH_CONTEXT_ONLY":
        readiness = "PARTIAL"

    elif not components:
        readiness = "DATA_BLOCKED"

    elif len(available_components) >= minimum_known_components:
        readiness = "READY_FOR_VALIDATION"

    elif available_components:
        readiness = "PARTIAL"

    else:
        readiness = "DATA_BLOCKED"

    return {
        "dimension": dimension_id,
        "declared_status": declared_status,
        "readiness": readiness,
        "components": components,
        "available_components": available_components,
        "missing_components": missing_components,
        "minimum_known_components": minimum_known_components,
        "required_future_metrics": future_metrics,
        "available_future_metrics": available_future_metrics,
        "missing_future_metrics": missing_future_metrics,
        "validation_required": bool(
            dimension.get("validation_required", True)
        ),
        "style_score_created": False,
        "arbitrary_weights_used": False,
    }


def build_readiness_report(
    spec: dict[str, Any],
    *,
    available_metrics: Iterable[str] | None = None,
) -> dict[str, Any]:
    dimensions = spec.get("dimensions")

    if not isinstance(dimensions, list):
        raise ValueError("spec dimensions must be a list")

    metrics = available_metric_set(available_metrics)

    assessments = [
        assess_dimension(
            dimension,
            available_metrics=metrics,
        )
        for dimension in dimensions
        if isinstance(dimension, dict)
    ]

    counts = {
        "READY_FOR_VALIDATION": 0,
        "PARTIAL": 0,
        "DATA_BLOCKED": 0,
    }

    for row in assessments:
        readiness = row["readiness"]

        if readiness in counts:
            counts[readiness] += 1

    return {
        "version": VERSION,
        "spec_version": spec.get("version"),
        "stage": 85,
        "status": "READINESS_ONLY",
        "available_stage84_metrics": sorted(metrics),
        "dimensions": assessments,
        "counts": counts,
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

    report = build_readiness_report(spec)

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