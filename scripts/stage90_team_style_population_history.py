#!/usr/bin/env python3
"""Stage90 — durable forward-only Team Style metric population history."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"

SOURCE = OPS / "team_style_metric_observations.jsonl"
OUT = OPS / "team_style_metric_population_history.jsonl"
META = OPS / "stage90_team_style_population_history_last_run.json"

VERSION = "PBK_STAGE90_TEAM_STYLE_POPULATION_HISTORY_V1"
SOURCE_VERSION = "PBK_STAGE84_TEAM_STYLE_METRIC_OBSERVATIONS_V1"


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
                    f"{path}:{line_number}: JSONL row must be object"
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


def profile_state_key(
    row: dict[str, Any],
) -> tuple[str, ...]:
    fixture_ids = row.get("window_fixture_ids")

    normalized_fixture_ids = (
        tuple(
            str(value)
            for value in fixture_ids
            if value is not None
            and str(value).strip()
        )
        if isinstance(fixture_ids, list)
        else ()
    )

    # Stage92 population-integrity dedupe is valid only when the
    # rolling-window fixture composition is explicitly known.
    #
    # Legacy Stage90 rows may not carry window_fixture_ids at all.
    # Treating every such row as the same empty composition would
    # collapse genuinely newer observations and change Stage90
    # forward-only behaviour.
    if normalized_fixture_ids:
        return (
            series_key(row)
            + ("FIXTURE_COMPOSITION",)
            + normalized_fixture_ids
        )

    return (
        observation_key(row)
        + ("LEGACY_OBSERVATION_IDENTITY",)
    )


def valid_source_row(
    row: dict[str, Any],
) -> bool:
    if (
        str(row.get("schema_version") or "")
        != SOURCE_VERSION
    ):
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


def latest_rows_by_series(
    rows: list[dict[str, Any]],
) -> dict[
    tuple[str, ...],
    dict[str, Any],
]:
    latest: dict[
        tuple[str, ...],
        dict[str, Any],
    ] = {}

    for row in rows:
        if not valid_source_row(row):
            continue

        key = series_key(row)
        timestamp = parse_iso(
            row.get("profile_before_utc")
        )

        current = latest.get(key)

        if current is None:
            latest[key] = row
            continue

        current_time = parse_iso(
            current.get("profile_before_utc")
        )

        if (
            current_time is None
            or timestamp > current_time
        ):
            latest[key] = row

    return latest


def existing_watermarks(
    rows: list[dict[str, Any]],
) -> dict[
    tuple[str, ...],
    datetime,
]:
    result: dict[
        tuple[str, ...],
        datetime,
    ] = {}

    for row in rows:
        key = series_key(row)
        timestamp = parse_iso(
            row.get("profile_before_utc")
        )

        if not all(key) or timestamp is None:
            continue

        current = result.get(key)

        if current is None or timestamp > current:
            result[key] = timestamp

    return result


def select_forward_candidates(
    source_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    valid_rows = [
        row
        for row in source_rows
        if valid_source_row(row)
    ]

    latest = latest_rows_by_series(valid_rows)
    watermarks = existing_watermarks(existing_rows)

    existing_states = {
        profile_state_key(row)
        for row in existing_rows
    }

    candidates: list[dict[str, Any]] = []

    for key, newest_row in latest.items():
        watermark = watermarks.get(key)

        # First sight:
        # bootstrap only the newest currently visible profile state.
        if watermark is None:
            state = profile_state_key(newest_row)

            if state not in existing_states:
                candidates.append(newest_row)

            continue

        # Existing series:
        # admit only genuinely newer profile states.
        newer_rows = []

        for row in valid_rows:
            if series_key(row) != key:
                continue

            timestamp = parse_iso(
                row.get("profile_before_utc")
            )

            if (
                timestamp is not None
                and timestamp > watermark
            ):
                newer_rows.append(row)

        # Same rolling-window fixture composition is the same
        # statistical profile state, even if the pipeline ran again
        # at a later profile_before_utc.
        state_candidates: dict[
            tuple[str, ...],
            dict[str, Any],
        ] = {}

        for row in sorted(
            newer_rows,
            key=lambda item: (
                parse_iso(
                    item.get("profile_before_utc")
                ),
                observation_key(item),
            ),
        ):
            state = profile_state_key(row)

            if state in existing_states:
                continue

            if state not in state_candidates:
                state_candidates[state] = row

        candidates.extend(
            state_candidates.values()
        )

    unique: dict[
        tuple[str, ...],
        dict[str, Any],
    ] = {}

    for row in candidates:
        unique[observation_key(row)] = row

    return sorted(
        unique.values(),
        key=lambda row: (
            parse_iso(
                row.get("profile_before_utc")
            ),
            observation_key(row),
        ),
    )

def history_row(
    source_row: dict[str, Any],
) -> dict[str, Any]:
    return {
        "version": VERSION,
        "source_version": SOURCE_VERSION,
        "source_profile_version": source_row.get(
            "source_profile_version"
        ),
        "profile_before_utc": source_row.get(
            "profile_before_utc"
        ),
        "observed_at_utc": source_row.get(
            "observed_at_utc"
        ),
        "league_id": source_row.get("league_id"),
        "league_name": source_row.get(
            "league_name"
        ),
        "season": source_row.get("season"),
        "team_id": source_row.get("team_id"),
        "team_name": source_row.get("team_name"),
        "split": str(
            source_row.get("split") or ""
        ).lower(),
        "window": source_row.get("window"),
        "metric": source_row.get("metric"),
        "value": source_row.get("value"),
        "metric_status": source_row.get(
            "metric_status"
        ),
        "sample_size": source_row.get(
            "sample_size"
        ),
        "coverage": source_row.get("coverage"),
        "window_actual_matches": source_row.get(
            "window_actual_matches"
        ),
        "window_complete": source_row.get(
            "window_complete"
        ),
        "window_fixture_ids": list(
            source_row.get("window_fixture_ids") or []
        ),
        "window_oldest_kickoff_utc": source_row.get(
            "window_oldest_kickoff_utc"
        ),
        "window_newest_kickoff_utc": source_row.get(
            "window_newest_kickoff_utc"
        ),
        "style_dimension_value": None,
        "historical_backfill": False,
        "first_seen_series_policy": (
            "LATEST_SNAPSHOT_ONLY"
        ),
        "existing_series_policy": (
            "STRICTLY_NEWER_THAN_WATERMARK"
        ),
        "missing_data_policy": (
            "UNKNOWN_NOT_ZERO"
        ),
        "population_sample_unit": (
            "DISTINCT_ROLLING_WINDOW_FIXTURE_COMPOSITION"
        ),
        "repeated_pipeline_snapshot_counts_as_new_sample": False,
        "research_only": True,
        "provider_calls_added": 0,
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
        status = "WAITING_FOR_STAGE84_OBSERVATIONS"

        write_json(
            META,
            {
                "version": VERSION,
                "source_version": SOURCE_VERSION,
                "run_at_utc": run_at,
                "status": status,
                "source_rows": 0,
                "existing_history_rows": len(
                    existing_rows
                ),
                "new_history_rows": 0,
                "total_history_rows": len(
                    existing_rows
                ),
                "historical_backfill": False,
                "provider_calls_added": 0,
                "research_only": True,
            },
        )

        print(status)
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
        history_row(row)
        for row in candidates
        if observation_key(row)
        not in existing_keys
    ]

    combined = existing_rows + new_rows

    if new_rows or OUT.exists():
        write_jsonl(
            OUT,
            combined,
        )

    status = (
        "APPENDED_FORWARD_POPULATION_HISTORY"
        if new_rows
        else "NO_NEW_FORWARD_POPULATION_HISTORY"
    )

    write_json(
        META,
        {
            "version": VERSION,
            "source_version": SOURCE_VERSION,
            "run_at_utc": run_at,
            "status": status,
            "source_rows": len(source_rows),
            "valid_source_rows": sum(
                1
                for row in source_rows
                if valid_source_row(row)
            ),
            "candidate_rows": len(candidates),
            "existing_history_rows": len(
                existing_rows
            ),
            "new_history_rows": len(new_rows),
            "total_history_rows": len(combined),
            "historical_backfill": False,
            "first_seen_series_policy": (
                "LATEST_SNAPSHOT_ONLY"
            ),
            "existing_series_policy": (
                "STRICTLY_NEWER_THAN_WATERMARK"
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
                "new_rows": len(new_rows),
                "total_rows": len(combined),
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
