#!/usr/bin/env python3
"""Stage93 — Team Style validation readiness from forward-labeled observations."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"

OBSERVATIONS = OPS / "team_style_dimension_validation_dataset.jsonl"
LABELS = OPS / "team_style_dimension_forward_labels.jsonl"

OUT = OPS / "team_style_validation_readiness.json"
META = OPS / "stage93_team_style_validation_readiness_last_run.json"

VERSION = "PBK_STAGE93_STYLE_VALIDATION_READINESS_V1"
OBSERVATION_VERSION = "PBK_STAGE88_STYLE_DIMENSION_VALIDATION_DATASET_V1"
LABEL_VERSION = "PBK_STAGE89_STYLE_DIMENSION_FORWARD_LABELS_V1"

MIN_LABELED_SAMPLES = 30

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


def readiness_group_key(
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
    if str(row.get("version") or "") != OBSERVATION_VERSION:
        return False

    if (
        str(row.get("validation_status") or "")
        != "UNLABELED_FORWARD_OBSERVATION"
    ):
        return False

    if str(row.get("dimension") or "") not in SUPPORTED_DIMENSIONS:
        return False

    if row.get("aggregation_performed") is not False:
        return False

    if row.get("dimension_value") is not None:
        return False

    return all(observation_key(row))


def valid_label(
    row: dict[str, Any],
) -> bool:
    if str(row.get("version") or "") != LABEL_VERSION:
        return False

    if str(row.get("dimension") or "") not in SUPPORTED_DIMENSIONS:
        return False

    return all(observation_key(row))


def build_readiness(
    observations: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    *,
    minimum_samples: int = MIN_LABELED_SAMPLES,
) -> list[dict[str, Any]]:
    observation_index: dict[
        tuple[str, ...],
        dict[str, Any],
    ] = {}

    for row in observations:
        if not valid_observation(row):
            continue

        observation_index[observation_key(row)] = row

    label_keys = {
        observation_key(row)
        for row in labels
        if valid_label(row)
    }

    grouped_observations: dict[
        tuple[str, ...],
        set[tuple[str, ...]],
    ] = defaultdict(set)

    grouped_labeled: dict[
        tuple[str, ...],
        set[tuple[str, ...]],
    ] = defaultdict(set)

    grouped_teams: dict[
        tuple[str, ...],
        set[str],
    ] = defaultdict(set)

    league_names: dict[
        tuple[str, ...],
        Any,
    ] = {}

    for key, row in observation_index.items():
        group = readiness_group_key(row)

        if not all(group):
            continue

        grouped_observations[group].add(key)

        team_id = str(row.get("team_id") or "").strip()

        if team_id:
            grouped_teams[group].add(team_id)

        if row.get("league_name"):
            league_names[group] = row.get("league_name")

        if key in label_keys:
            grouped_labeled[group].add(key)

    results: list[dict[str, Any]] = []

    for group in sorted(grouped_observations):
        (
            league_id,
            season,
            split,
            window,
            dimension,
        ) = group

        observation_n = len(
            grouped_observations[group]
        )
        labeled_n = len(
            grouped_labeled[group]
        )
        team_n = len(
            grouped_teams[group]
        )

        if labeled_n == 0:
            status = "NO_LABELED_SAMPLES"
        elif labeled_n < minimum_samples:
            status = "INSUFFICIENT_DATA"
        else:
            status = "READY"

        results.append(
            {
                "version": VERSION,
                "league_id": league_id,
                "league_name": league_names.get(group),
                "season": season,
                "split": split,
                "window": int(window),
                "dimension": dimension,
                "forward_observation_n": observation_n,
                "forward_labeled_sample_n": labeled_n,
                "distinct_team_n": team_n,
                "minimum_labeled_samples": minimum_samples,
                "readiness_status": status,
                "sample_identity": (
                    "STAGE88_OBSERVATION_KEY_WITH_STAGE89_FORWARD_LABEL"
                ),
                "historical_backfill": False,
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

    rows = build_readiness(
        observations,
        labels,
    )

    payload = {
        "version": VERSION,
        "run_at_utc": run_at,
        "minimum_labeled_samples": (
            MIN_LABELED_SAMPLES
        ),
        "groups": rows,
    }

    write_json(OUT, payload)

    write_json(
        META,
        {
            "version": VERSION,
            "run_at_utc": run_at,
            "source_observation_rows": len(
                observations
            ),
            "source_label_rows": len(labels),
            "readiness_groups": len(rows),
            "ready_groups": sum(
                1
                for row in rows
                if row["readiness_status"]
                == "READY"
            ),
            "output": str(
                OUT.relative_to(ROOT)
            ),
            "research_only": True,
            "provider_calls_added": 0,
            "probability_mutation": False,
            "eligibility_mutation": False,
            "creates_signal": False,
        },
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
