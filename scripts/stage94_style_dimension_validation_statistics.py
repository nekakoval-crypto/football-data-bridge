#!/usr/bin/env python3
"""Stage94 — forward statistical evidence for Team Style dimensions."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"

OBSERVATIONS = OPS / "team_style_dimension_validation_dataset.jsonl"
LABELS = OPS / "team_style_dimension_forward_labels.jsonl"
READINESS = OPS / "team_style_validation_readiness.json"

OUT = OPS / "team_style_dimension_validation_statistics.json"
META = OPS / "stage94_team_style_validation_statistics_last_run.json"

VERSION = "PBK_STAGE94_STYLE_DIMENSION_VALIDATION_STATISTICS_V1"

OBSERVATION_VERSION = (
    "PBK_STAGE88_STYLE_DIMENSION_VALIDATION_DATASET_V1"
)
LABEL_VERSION = (
    "PBK_STAGE89_STYLE_DIMENSION_FORWARD_LABELS_V1"
)
READINESS_VERSION = (
    "PBK_STAGE93_STYLE_VALIDATION_READINESS_V1"
)

MIN_PAIRED_SAMPLES = 30

SUPPORTED_DIMENSIONS = {
    "ATTACK_VOLUME",
    "POSSESSION_CONTROL",
    "DEFENSIVE_RESISTANCE",
}


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def fnum(value: Any) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(result):
        return None

    return result


def read_json(path: Path) -> Any:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()

            if not text:
                continue

            payload = json.loads(text)

            if not isinstance(payload, dict):
                raise ValueError(
                    f"{path}:{line_number}: JSONL row must be object"
                )

            rows.append(payload)

    return rows


def write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")


def observation_key(
    row: dict[str, Any],
) -> tuple[str, ...]:
    return (
        str(row.get("league_id") or ""),
        str(row.get("season") or ""),
        str(row.get("team_id") or ""),
        str(row.get("split") or "").lower(),
        str(row.get("window") or ""),
        str(row.get("dimension") or ""),
        str(row.get("profile_before_utc") or ""),
    )


def group_key(
    row: dict[str, Any],
) -> tuple[str, ...]:
    return (
        str(row.get("league_id") or ""),
        str(row.get("season") or ""),
        str(row.get("split") or "").lower(),
        str(row.get("window") or ""),
        str(row.get("dimension") or ""),
    )


def valid_observation(
    row: dict[str, Any],
) -> bool:
    return (
        str(row.get("version") or "")
        == OBSERVATION_VERSION
        and str(row.get("dimension") or "")
        in SUPPORTED_DIMENSIONS
        and str(row.get("validation_status") or "")
        == "UNLABELED_FORWARD_OBSERVATION"
        and row.get("aggregation_performed") is False
        and all(observation_key(row))
    )


def valid_label(
    row: dict[str, Any],
) -> bool:
    return (
        str(row.get("version") or "")
        == LABEL_VERSION
        and str(row.get("dimension") or "")
        in SUPPORTED_DIMENSIONS
        and str(row.get("label_status") or "")
        == "FORWARD_MATCH_ATTACHED"
        and isinstance(row.get("forward_outcomes"), dict)
        and all(observation_key(row))
    )


def ready_groups(
    payload: Any,
) -> set[tuple[str, ...]]:
    result: set[tuple[str, ...]] = set()

    if not isinstance(payload, dict):
        return result

    if (
        str(payload.get("version") or "")
        != READINESS_VERSION
    ):
        return result

    for row in payload.get("groups") or []:
        if (
            str(row.get("readiness_status") or "")
            != "READY"
        ):
            continue

        key = group_key(row)

        if all(key):
            result.add(key)

    return result


def pearson(
    xs: list[float],
    ys: list[float],
) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None

    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)

    numerator = sum(
        (x - x_mean) * (y - y_mean)
        for x, y in zip(xs, ys)
    )

    x_ss = sum(
        (x - x_mean) ** 2
        for x in xs
    )
    y_ss = sum(
        (y - y_mean) ** 2
        for y in ys
    )

    if x_ss <= 0 or y_ss <= 0:
        return None

    return numerator / math.sqrt(x_ss * y_ss)


def quartile_outcomes(
    pairs: list[tuple[float, float]],
) -> tuple[
    float | None,
    float | None,
    float | None,
]:
    if len(pairs) < 4:
        return None, None, None

    ordered = sorted(
        pairs,
        key=lambda pair: pair[0],
    )

    q = max(1, len(ordered) // 4)

    lower = [
        outcome
        for _, outcome in ordered[:q]
    ]
    upper = [
        outcome
        for _, outcome in ordered[-q:]
    ]

    lower_mean = sum(lower) / len(lower)
    upper_mean = sum(upper) / len(upper)

    return (
        lower_mean,
        upper_mean,
        upper_mean - lower_mean,
    )


def build_statistics(
    observations: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    readiness_payload: Any,
    *,
    minimum_samples: int = MIN_PAIRED_SAMPLES,
) -> list[dict[str, Any]]:

    ready = ready_groups(readiness_payload)

    observation_index = {
        observation_key(row): row
        for row in observations
        if valid_observation(row)
    }

    label_index = {
        observation_key(row): row
        for row in labels
        if valid_label(row)
    }

    samples: dict[
        tuple[str, ...],
        dict[
            str,
            list[tuple[float, float]],
        ],
    ] = defaultdict(
        lambda: defaultdict(list)
    )

    component_directions: dict[
        tuple[tuple[str, ...], str],
        Any,
    ] = {}

    league_names: dict[
        tuple[str, ...],
        Any,
    ] = {}

    for key, observation in observation_index.items():
        label = label_index.get(key)

        if label is None:
            continue

        group = group_key(observation)

        if group not in ready:
            continue

        if observation.get("league_name"):
            league_names[group] = observation.get(
                "league_name"
            )

        outcomes = label.get("forward_outcomes") or {}

        for component in observation.get(
            "components"
        ) or []:
            metric = str(
                component.get("metric") or ""
            ).strip()

            if not metric:
                continue

            predictor = fnum(
                component.get("z_score")
            )
            outcome = fnum(
                outcomes.get(metric)
            )

            if predictor is None or outcome is None:
                continue

            samples[group][metric].append(
                (
                    predictor,
                    outcome,
                )
            )

            component_directions[
                (group, metric)
            ] = component.get("direction")

    results: list[dict[str, Any]] = []

    for group in sorted(ready):
        (
            league_id,
            season,
            split,
            window,
            dimension,
        ) = group

        component_rows = []

        for metric in sorted(
            samples.get(group, {})
        ):
            pairs = samples[group][metric]

            xs = [
                predictor
                for predictor, _ in pairs
            ]
            ys = [
                outcome
                for _, outcome in pairs
            ]

            r = pearson(xs, ys)

            (
                lower_mean,
                upper_mean,
                quartile_delta,
            ) = quartile_outcomes(pairs)

            paired_n = len(pairs)

            if paired_n < minimum_samples:
                status = (
                    "INSUFFICIENT_PAIRED_SAMPLES"
                )
            else:
                status = (
                    "VALIDATION_EVIDENCE_AVAILABLE"
                )

            component_rows.append(
                {
                    "metric": metric,
                    "direction": (
                        component_directions.get(
                            (group, metric)
                        )
                    ),
                    "paired_sample_n": paired_n,
                    "minimum_paired_samples": (
                        minimum_samples
                    ),
                    "pearson_r": r,
                    "lower_quartile_forward_mean": (
                        lower_mean
                    ),
                    "upper_quartile_forward_mean": (
                        upper_mean
                    ),
                    "upper_minus_lower_forward_mean": (
                        quartile_delta
                    ),
                    "validation_status": status,
                }
            )

        if not component_rows:
            group_status = (
                "NO_MATCHED_COMPONENT_OUTCOMES"
            )
        elif any(
            row["validation_status"]
            == "VALIDATION_EVIDENCE_AVAILABLE"
            for row in component_rows
        ):
            group_status = (
                "VALIDATION_EVIDENCE_AVAILABLE"
            )
        else:
            group_status = (
                "INSUFFICIENT_PAIRED_SAMPLES"
            )

        results.append(
            {
                "version": VERSION,
                "league_id": league_id,
                "league_name": (
                    league_names.get(group)
                ),
                "season": season,
                "split": split,
                "window": int(window),
                "dimension": dimension,
                "validation_status": group_status,
                "components": component_rows,
                "automatic_validation_decision": False,
                "validation_threshold_policy_defined": False,
                "historical_backfill": False,
                "first_next_match_required": True,
                "later_match_fallback_allowed": False,
                "research_only": True,
                "provider_calls_added": 0,
                "probability_mutation": False,
                "eligibility_mutation": False,
                "creates_signal": False,
                "stake_changes": False,
                "forward_journal_mutation": False,
                "r1_r2_r3_mutation": False,
                "ui_changes": False,
                "api_changes": False,
            }
        )

    return results


def main() -> int:
    run_at = utc_now()

    observations = read_jsonl(OBSERVATIONS)
    labels = read_jsonl(LABELS)
    readiness_payload = read_json(READINESS)

    rows = build_statistics(
        observations,
        labels,
        readiness_payload,
    )

    payload = {
        "version": VERSION,
        "run_at_utc": run_at,
        "minimum_paired_samples": (
            MIN_PAIRED_SAMPLES
        ),
        "groups": rows,
        "automatic_validation_decision": False,
        "validation_threshold_policy_defined": False,
    }

    write_json(
        OUT,
        payload,
    )

    write_json(
        META,
        {
            "version": VERSION,
            "run_at_utc": run_at,
            "source_observations": len(
                observations
            ),
            "source_labels": len(labels),
            "validation_groups": len(rows),
            "evidence_available_groups": sum(
                1
                for row in rows
                if row["validation_status"]
                == "VALIDATION_EVIDENCE_AVAILABLE"
            ),
            "output": str(
                OUT.relative_to(ROOT)
            ),
            "research_only": True,
            "probability_mutation": False,
            "eligibility_mutation": False,
            "creates_signal": False,
        },
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
