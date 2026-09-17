#!/usr/bin/env python3
"""Stage88 — forward-only Team Style dimension validation dataset."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"

SOURCE = OPS / "team_style_dimension_evidence.jsonl"
OUT = OPS / "team_style_dimension_validation_dataset.jsonl"
META = OPS / "stage88_team_style_dimension_validation_last_run.json"

VERSION = "PBK_STAGE88_STYLE_DIMENSION_VALIDATION_DATASET_V1"
SOURCE_VERSION = "PBK_STAGE87_NORMALIZED_STYLE_DIMENSION_EVIDENCE_V1"

READY_STATUS = "READY_FOR_VALIDATION"


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_iso(value: Any) -> datetime | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        result = datetime.fromisoformat(text)
    except ValueError:
        return None

    if result.tzinfo is None:
        return None

    return result.astimezone(timezone.utc)


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")


def series_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("league_id") or ""),
        str(row.get("season") or ""),
        str(row.get("team_id") or ""),
        str(row.get("split") or "").lower(),
        str(row.get("window") or ""),
        str(row.get("dimension") or ""),
    )


def observation_key(row: dict[str, Any]) -> tuple[str, ...]:
    return series_key(row) + (
        str(row.get("profile_before_utc") or ""),
    )


def valid_ready_source_row(row: dict[str, Any]) -> bool:
    if str(row.get("dimension_status") or "").upper() != READY_STATUS:
        return False

    if not all(series_key(row)):
        return False

    if parse_iso(row.get("profile_before_utc")) is None:
        return False

    if row.get("dimension_value") is not None:
        return False

    if row.get("aggregation_performed") is not False:
        return False

    return True


def existing_watermarks(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, ...], datetime]:
    watermarks: dict[tuple[str, ...], datetime] = {}

    for row in rows:
        key = series_key(row)
        timestamp = parse_iso(row.get("profile_before_utc"))

        if not all(key) or timestamp is None:
            continue

        current = watermarks.get(key)

        if current is None or timestamp > current:
            watermarks[key] = timestamp

    return watermarks


def latest_ready_rows_by_series(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, ...], dict[str, Any]]:
    latest: dict[tuple[str, ...], dict[str, Any]] = {}

    for row in rows:
        if not valid_ready_source_row(row):
            continue

        key = series_key(row)
        timestamp = parse_iso(row.get("profile_before_utc"))

        current = latest.get(key)

        if current is None:
            latest[key] = row
            continue

        current_timestamp = parse_iso(
            current.get("profile_before_utc")
        )

        if (
            current_timestamp is None
            or timestamp > current_timestamp
        ):
            latest[key] = row

    return latest


def select_forward_candidates(
    source_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ready_rows = [
        row
        for row in source_rows
        if valid_ready_source_row(row)
    ]

    watermarks = existing_watermarks(existing_rows)
    latest = latest_ready_rows_by_series(ready_rows)

    candidates: list[dict[str, Any]] = []

    for key, newest_row in latest.items():
        watermark = watermarks.get(key)

        # First sight: admit only the newest available observation.
        if watermark is None:
            candidates.append(newest_row)
            continue

        # Existing series: admit every genuinely newer observation.
        for row in ready_rows:
            if series_key(row) != key:
                continue

            timestamp = parse_iso(
                row.get("profile_before_utc")
            )

            if timestamp is not None and timestamp > watermark:
                candidates.append(row)

    unique: dict[
        tuple[str, ...],
        dict[str, Any],
    ] = {}

    for row in candidates:
        unique[observation_key(row)] = row

    return sorted(
        unique.values(),
        key=lambda row: (
            parse_iso(row.get("profile_before_utc")),
            observation_key(row),
        ),
    )


def validation_row(
    source_row: dict[str, Any],
) -> dict[str, Any]:
    components = []

    for component in source_row.get("components") or []:
        components.append(
            {
                "metric": component.get("metric"),
                "direction": component.get("direction"),
                "availability": component.get("availability"),
                "known": bool(component.get("known")),
                "normalization_status": component.get(
                    "normalization_status"
                ),
                "raw_value": component.get("raw_value"),
                "population_n": component.get("population_n"),
                "percentile": component.get("percentile"),
                "z_score": component.get("z_score"),
            }
        )

    return {
        "version": VERSION,
        "source_version": SOURCE_VERSION,
        "league_id": source_row.get("league_id"),
        "league_name": source_row.get("league_name"),
        "season": source_row.get("season"),
        "team_id": source_row.get("team_id"),
        "split": str(source_row.get("split") or "").lower(),
        "window": source_row.get("window"),
        "dimension": source_row.get("dimension"),
        "profile_before_utc": source_row.get(
            "profile_before_utc"
        ),
        "observed_at_utc": source_row.get(
            "observed_at_utc"
        ),
        "known_components": source_row.get(
            "known_components"
        ),
        "minimum_known_components": source_row.get(
            "minimum_known_components"
        ),
        "components": components,
        "dimension_value": None,
        "validation_status": (
            "UNLABELED_FORWARD_OBSERVATION"
        ),
        "validation_result": None,
        "aggregation_performed": False,
        "arbitrary_weights_used": False,
        "zero_to_ten_score": False,
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


def main() -> int:
    run_at = utc_now()

    source_rows = read_jsonl(SOURCE)
    existing_rows = read_jsonl(OUT)

    if not source_rows:
        write_json(
            META,
            {
                "version": VERSION,
                "run_at_utc": run_at,
                "status": (
                    "WAITING_FOR_STAGE87_DIMENSION_EVIDENCE"
                ),
                "source_rows": 0,
                "existing_validation_rows": len(
                    existing_rows
                ),
                "new_validation_rows": 0,
                "total_validation_rows": len(
                    existing_rows
                ),
                "historical_backfill": False,
                "provider_calls_added": 0,
                "research_only": True,
            },
        )

        print(
            "WAITING_FOR_STAGE87_DIMENSION_EVIDENCE"
        )
        return 0

    candidates = select_forward_candidates(
        source_rows,
        existing_rows,
    )

    existing_keys = {
        observation_key(row)
        for row in existing_rows
    }

    new_rows = [
        validation_row(row)
        for row in candidates
        if observation_key(row) not in existing_keys
    ]

    combined = existing_rows + new_rows

    if new_rows or OUT.exists():
        write_jsonl(OUT, combined)

    status = (
        "APPENDED_FORWARD_VALIDATION_OBSERVATIONS"
        if new_rows
        else "NO_NEW_FORWARD_VALIDATION_OBSERVATIONS"
    )

    write_json(
        META,
        {
            "version": VERSION,
            "source_version": SOURCE_VERSION,
            "run_at_utc": run_at,
            "status": status,
            "source_rows": len(source_rows),
            "ready_source_rows": sum(
                1
                for row in source_rows
                if valid_ready_source_row(row)
            ),
            "candidate_rows": len(candidates),
            "existing_validation_rows": len(
                existing_rows
            ),
            "new_validation_rows": len(new_rows),
            "total_validation_rows": len(combined),
            "first_seen_series_policy": (
                "LATEST_SNAPSHOT_ONLY"
            ),
            "existing_series_policy": (
                "STRICTLY_NEWER_THAN_WATERMARK"
            ),
            "validation_status": (
                "UNLABELED_FORWARD_OBSERVATIONS_ONLY"
            ),
            "dimension_value_created": False,
            "aggregation_performed": False,
            "historical_backfill": False,
            "provider_calls_added": 0,
            "research_only": True,
            "probability_mutation": False,
            "eligibility_mutation": False,
            "creates_signal": False,
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
                "source_rows": len(source_rows),
                "new_rows": len(new_rows),
                "total_rows": len(combined),
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
