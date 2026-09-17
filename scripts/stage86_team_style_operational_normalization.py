#!/usr/bin/env python3
"""Stage86 — forward-only operational normalized Team Style metrics.

Stage91 migration:
normalization now consumes the durable Stage90 population history instead of
the transient Stage84 current snapshot.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.stage84_team_style_metric_normalization import (
        MIN_POPULATION,
        VERSION as STAGE84_NORMALIZATION_VERSION,
        normalize_against_population,
        parse_iso,
    )
except ModuleNotFoundError:
    from stage84_team_style_metric_normalization import (
        MIN_POPULATION,
        VERSION as STAGE84_NORMALIZATION_VERSION,
        normalize_against_population,
        parse_iso,
    )


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"

SOURCE = OPS / "team_style_metric_population_history.jsonl"
OUT = OPS / "team_style_normalized_observations.jsonl"
META = OPS / "stage86_team_style_normalization_last_run.json"

VERSION = "PBK_STAGE86_OPERATIONAL_NORMALIZED_STYLE_METRICS_V1"
POPULATION_SOURCE_VERSION = "PBK_STAGE90_TEAM_STYLE_POPULATION_HISTORY_V1"


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
                    f"{path}:{line_number}: JSONL row must be an object"
                )

            rows.append(payload)

    return rows


def write_jsonl(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )


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


def series_key(
    row: dict[str, Any],
) -> tuple[str, ...]:
    return (
        str(row.get("league_id") or ""),
        str(row.get("season") or ""),
        str(row.get("team_id") or ""),
        str(row.get("split") or "").lower(),
        str(row.get("window") or ""),
        str(row.get("metric") or ""),
    )


def observation_key(
    row: dict[str, Any],
) -> tuple[str, ...]:
    return series_key(row) + (
        str(row.get("profile_before_utc") or ""),
    )


def valid_source_row(
    row: dict[str, Any],
) -> bool:
    if str(row.get("version") or "") != POPULATION_SOURCE_VERSION:
        return False

    if not all(series_key(row)):
        return False

    profile_before = parse_iso(
        row.get("profile_before_utc")
    )
    observed_at = parse_iso(
        row.get("observed_at_utc")
    )

    if profile_before is None or observed_at is None:
        return False

    if observed_at > profile_before:
        return False

    return True


def select_forward_candidates(
    source_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_keys = {
        observation_key(row)
        for row in existing_rows
        if all(observation_key(row))
    }

    unique: dict[
        tuple[str, ...],
        dict[str, Any],
    ] = {}

    for row in source_rows:
        if not valid_source_row(row):
            continue

        key = observation_key(row)

        if key in existing_keys:
            continue

        unique[key] = row

    return sorted(
        unique.values(),
        key=lambda row: (
            parse_iso(
                row.get("profile_before_utc")
            ),
            observation_key(row),
        ),
    )


def normalize_row(
    target_row: dict[str, Any],
    source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    cutoff = str(
        target_row.get("profile_before_utc")
        or ""
    )

    population_rows = [
        row
        for row in source_rows
        if (
            valid_source_row(row)
            and str(
                row.get("metric_status")
                or ""
            ).upper()
            == "KNOWN"
        )
    ]

    effective_target = dict(target_row)

    if (
        str(
            effective_target.get(
                "metric_status"
            )
            or ""
        ).upper()
        != "KNOWN"
    ):
        effective_target["value"] = None

    result = normalize_against_population(
        target_row=effective_target,
        population_rows=population_rows,
        before_utc=cutoff,
        min_population=MIN_POPULATION,
    )

    normalized = (
        result.get("normalized")
        or {}
    )

    return {
        "version": VERSION,
        "normalization_source_version": (
            STAGE84_NORMALIZATION_VERSION
        ),
        "population_source_version": (
            POPULATION_SOURCE_VERSION
        ),
        "league_id": target_row.get(
            "league_id"
        ),
        "league_name": target_row.get(
            "league_name"
        ),
        "season": target_row.get("season"),
        "team_id": target_row.get(
            "team_id"
        ),
        "split": str(
            target_row.get("split")
            or ""
        ).lower(),
        "window": target_row.get("window"),
        "metric": target_row.get("metric"),
        "profile_before_utc": (
            target_row.get(
                "profile_before_utc"
            )
        ),
        "observed_at_utc": (
            target_row.get(
                "observed_at_utc"
            )
        ),
        "raw_metric_status": (
            target_row.get(
                "metric_status"
            )
        ),
        "raw_value": normalized.get(
            "raw_value"
        ),
        "population_n": normalized.get(
            "population_n"
        ),
        "population_mean": normalized.get(
            "population_mean"
        ),
        "population_std": normalized.get(
            "population_std"
        ),
        "percentile": normalized.get(
            "percentile"
        ),
        "z_score": normalized.get(
            "z_score"
        ),
        "normalization_status": (
            result.get("status")
        ),
        "minimum_population": (
            MIN_POPULATION
        ),
        "minimum_population_policy": (
            "CALIBRATION_MIN_SAMPLE_POLICY"
        ),
        "validated_performance_threshold": False,
        "research_only": True,
        "provider_calls_added": 0,
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


def main() -> int:
    run_at = utc_now()

    source_rows = read_jsonl(SOURCE)
    existing_rows = read_jsonl(OUT)

    if not source_rows:
        write_json(
            META,
            {
                "version": VERSION,
                "population_source_version": (
                    POPULATION_SOURCE_VERSION
                ),
                "run_at_utc": run_at,
                "status": (
                    "WAITING_FOR_STAGE90_POPULATION_HISTORY"
                ),
                "source_rows": 0,
                "existing_normalized_rows": len(
                    existing_rows
                ),
                "new_normalized_rows": 0,
                "total_normalized_rows": len(
                    existing_rows
                ),
                "provider_calls_added": 0,
                "historical_backfill": False,
                "research_only": True,
            },
        )

        print(
            "WAITING_FOR_STAGE90_POPULATION_HISTORY"
        )
        return 0

    valid_rows = [
        row
        for row in source_rows
        if valid_source_row(row)
    ]

    candidates = select_forward_candidates(
        source_rows,
        existing_rows,
    )

    new_rows = [
        normalize_row(
            row,
            valid_rows,
        )
        for row in candidates
    ]

    combined = (
        existing_rows
        + new_rows
    )

    if new_rows or OUT.exists():
        write_jsonl(
            OUT,
            combined,
        )

    status = (
        "NORMALIZED_NEW_OBSERVATIONS"
        if new_rows
        else "NO_NEW_FORWARD_OBSERVATIONS"
    )

    write_json(
        META,
        {
            "version": VERSION,
            "normalization_source_version": (
                STAGE84_NORMALIZATION_VERSION
            ),
            "population_source_version": (
                POPULATION_SOURCE_VERSION
            ),
            "run_at_utc": run_at,
            "status": status,
            "source_rows": len(
                source_rows
            ),
            "valid_population_rows": len(
                valid_rows
            ),
            "candidate_rows": len(
                candidates
            ),
            "existing_normalized_rows": len(
                existing_rows
            ),
            "new_normalized_rows": len(
                new_rows
            ),
            "total_normalized_rows": len(
                combined
            ),
            "minimum_population": (
                MIN_POPULATION
            ),
            "minimum_population_policy": (
                "CALIBRATION_MIN_SAMPLE_POLICY"
            ),
            "historical_backfill": False,
            "candidate_source_policy": (
                "ALL_UNNORMALIZED_STAGE90_FORWARD_OBSERVATIONS"
            ),
            "population_source_policy": (
                "DURABLE_STAGE90_HISTORY_UP_TO_TARGET_CUTOFF"
            ),
            "missing_data_policy": (
                "UNKNOWN_NOT_ZERO"
            ),
            "provider_calls_added": 0,
            "research_only": True,
            "creates_signal": False,
            "probability_mutation": False,
            "eligibility_mutation": False,
            "stake_changes": False,
            "forward_journal_mutation": False,
            "r1_r2_r3_mutation": False,
            "ui_changes": False,
            "api_changes": False,
        },
    )

    print(
        json.dumps(
            {
                "status": status,
                "source_rows": len(
                    source_rows
                ),
                "valid_rows": len(
                    valid_rows
                ),
                "new_rows": len(
                    new_rows
                ),
                "total_rows": len(
                    combined
                ),
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
