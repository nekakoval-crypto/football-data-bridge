#!/usr/bin/env python3
"""Stage89 — forward labels for Team Style dimension validation observations."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"

SOURCE = OPS / "team_style_dimension_validation_dataset.jsonl"
STATS = OPS / "team_match_statistics.csv"
BACKLOG = OPS / "stage81_team_stats_backlog.csv"

OUT = OPS / "team_style_dimension_forward_labels.jsonl"
META = OPS / "stage89_team_style_dimension_forward_labels_last_run.json"

VERSION = "PBK_STAGE89_STYLE_DIMENSION_FORWARD_LABELS_V1"
SOURCE_VERSION = "PBK_STAGE88_STYLE_DIMENSION_VALIDATION_DATASET_V1"

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


def fnum(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


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


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


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


def valid_source_observation(
    row: dict[str, Any],
) -> bool:
    if str(row.get("version") or "") != SOURCE_VERSION:
        return False

    if (
        str(row.get("validation_status") or "")
        != "UNLABELED_FORWARD_OBSERVATION"
    ):
        return False

    if str(row.get("dimension") or "") not in SUPPORTED_DIMENSIONS:
        return False

    if row.get("dimension_value") is not None:
        return False

    if parse_iso(row.get("profile_before_utc")) is None:
        return False

    return all(observation_key(row))


def stats_index(
    rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}

    for row in rows:
        fixture_id = str(row.get("fixture_id") or "").strip()

        if not fixture_id:
            continue

        result.setdefault(fixture_id, []).append(row)

    return result


def team_name_index(
    stats_rows: list[dict[str, Any]],
) -> dict[tuple[str, str, str], str]:
    result: dict[tuple[str, str, str], str] = {}

    for row in stats_rows:
        league_id = str(
            row.get("provider_league_id") or ""
        ).strip()
        season = str(row.get("season") or "").strip()
        team_id = str(row.get("team_id") or "").strip()
        team_name = str(row.get("team_name") or "").strip()

        key = (
            league_id,
            season,
            team_id,
        )

        if all(key) and team_name:
            result[key] = team_name

    return result


def backlog_candidates(
    observation: dict[str, Any],
    team_name: str,
    backlog_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    league_id = str(observation.get("league_id") or "")
    season = str(observation.get("season") or "")
    cutoff = parse_iso(
        observation.get("profile_before_utc")
    )

    if cutoff is None:
        return []

    candidates: list[dict[str, Any]] = []

    normalized_team_name = team_name.strip().casefold()

    for row in backlog_rows:
        row_league = str(
            row.get("provider_league_id") or ""
        ).strip()
        row_season = str(row.get("season") or "").strip()

        if row_league != league_id or row_season != season:
            continue

        kickoff = parse_iso(row.get("kickoff_utc"))

        if kickoff is None or kickoff <= cutoff:
            continue

        home = str(row.get("home_team") or "").strip()
        away = str(row.get("away_team") or "").strip()

        if normalized_team_name not in {
            home.casefold(),
            away.casefold(),
        }:
            continue

        candidates.append(row)

    return sorted(
        candidates,
        key=lambda row: (
            parse_iso(row.get("kickoff_utc")),
            str(row.get("fixture_id") or ""),
        ),
    )


def complete_fixture_pair(
    fixture_id: str,
    team_id: str,
    indexed_stats: dict[
        str,
        list[dict[str, Any]],
    ],
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
]:
    rows = indexed_stats.get(fixture_id, [])

    own = next(
        (
            row
            for row in rows
            if str(row.get("team_id") or "").strip()
            == team_id
        ),
        None,
    )

    opponent = next(
        (
            row
            for row in rows
            if str(row.get("team_id") or "").strip()
            and str(row.get("team_id") or "").strip()
            != team_id
        ),
        None,
    )

    if own is None or opponent is None:
        return None, None

    return own, opponent


def outcome_payload(
    dimension: str,
    own: dict[str, Any],
    opponent: dict[str, Any],
) -> dict[str, Any]:
    if dimension == "ATTACK_VOLUME":
        return {
            "shots_for": fnum(own.get("shots_total")),
            "sot_for": fnum(own.get("shots_on_goal")),
            "xg_for": fnum(own.get("expected_goals")),
            "corners_for": fnum(own.get("corners")),
        }

    if dimension == "POSSESSION_CONTROL":
        return {
            "possession_pct": fnum(
                own.get("possession_pct")
            ),
            "passes_total": fnum(
                own.get("passes_total")
            ),
            "pass_accuracy_pct": fnum(
                own.get("passes_accuracy_pct")
            ),
        }

    if dimension == "DEFENSIVE_RESISTANCE":
        return {
            "shots_against": fnum(
                opponent.get("shots_total")
            ),
            "sot_against": fnum(
                opponent.get("shots_on_goal")
            ),
            "xg_against": fnum(
                opponent.get("expected_goals")
            ),
            "corners_against": fnum(
                opponent.get("corners")
            ),
        }

    return {}


def label_row(
    observation: dict[str, Any],
    backlog_row: dict[str, Any],
    own: dict[str, Any],
    opponent: dict[str, Any],
) -> dict[str, Any]:
    dimension = str(observation.get("dimension") or "")

    return {
        "version": VERSION,
        "source_version": SOURCE_VERSION,
        "league_id": observation.get("league_id"),
        "league_name": observation.get("league_name"),
        "season": observation.get("season"),
        "team_id": observation.get("team_id"),
        "team_name": own.get("team_name"),
        "split": observation.get("split"),
        "window": observation.get("window"),
        "dimension": dimension,
        "profile_before_utc": observation.get(
            "profile_before_utc"
        ),
        "source_observed_at_utc": observation.get(
            "observed_at_utc"
        ),
        "fixture_id": backlog_row.get("fixture_id"),
        "fixture_kickoff_utc": backlog_row.get(
            "kickoff_utc"
        ),
        "fixture_round": backlog_row.get("round"),
        "side": own.get("side"),
        "opponent_team_id": opponent.get("team_id"),
        "opponent_name": opponent.get("team_name"),
        "stats_observed_at_utc": own.get(
            "observed_at_utc"
        ),
        "forward_outcomes": outcome_payload(
            dimension,
            own,
            opponent,
        ),
        "label_status": "FORWARD_MATCH_ATTACHED",
        "validation_result": None,
        "dimension_value": None,
        "aggregation_performed": False,
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


def build_forward_labels(
    observations: list[dict[str, Any]],
    stats_rows: list[dict[str, Any]],
    backlog_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, int],
]:
    indexed_stats = stats_index(stats_rows)
    names = team_name_index(stats_rows)

    existing_keys = {
        observation_key(row)
        for row in existing_rows
    }

    new_rows: list[dict[str, Any]] = []

    counters = {
        "source_observations": 0,
        "already_labeled": 0,
        "team_name_unknown": 0,
        "no_next_fixture_known": 0,
        "first_next_fixture_stats_pending": 0,
        "labeled": 0,
    }

    for observation in observations:
        if not valid_source_observation(observation):
            continue

        counters["source_observations"] += 1

        key = observation_key(observation)

        if key in existing_keys:
            counters["already_labeled"] += 1
            continue

        league_id = str(
            observation.get("league_id") or ""
        )
        season = str(observation.get("season") or "")
        team_id = str(observation.get("team_id") or "")

        team_name = names.get(
            (
                league_id,
                season,
                team_id,
            )
        )

        if not team_name:
            counters["team_name_unknown"] += 1
            continue

        next_fixtures = backlog_candidates(
            observation,
            team_name,
            backlog_rows,
        )

        if not next_fixtures:
            counters["no_next_fixture_known"] += 1
            continue

        # Critical anti-lookahead rule:
        # only the FIRST known subsequent fixture may label the observation.
        first_fixture = next_fixtures[0]

        fixture_id = str(
            first_fixture.get("fixture_id") or ""
        ).strip()

        own, opponent = complete_fixture_pair(
            fixture_id,
            team_id,
            indexed_stats,
        )

        if own is None or opponent is None:
            counters[
                "first_next_fixture_stats_pending"
            ] += 1
            continue

        new_rows.append(
            label_row(
                observation,
                first_fixture,
                own,
                opponent,
            )
        )
        counters["labeled"] += 1

    return new_rows, counters


def main() -> int:
    run_at = utc_now()

    observations = read_jsonl(SOURCE)
    stats_rows = read_csv(STATS)
    backlog_rows = read_csv(BACKLOG)
    existing_rows = read_jsonl(OUT)

    if not observations:
        status = (
            "WAITING_FOR_STAGE88_VALIDATION_OBSERVATIONS"
        )

        write_json(
            META,
            {
                "version": VERSION,
                "run_at_utc": run_at,
                "status": status,
                "source_observations": 0,
                "new_labels": 0,
                "total_labels": len(existing_rows),
                "provider_calls_added": 0,
                "research_only": True,
            },
        )

        print(status)
        return 0

    new_rows, counters = build_forward_labels(
        observations,
        stats_rows,
        backlog_rows,
        existing_rows,
    )

    combined = existing_rows + new_rows

    if new_rows or OUT.exists():
        write_jsonl(OUT, combined)

    if new_rows:
        status = "APPENDED_FORWARD_LABELS"
    elif counters["first_next_fixture_stats_pending"]:
        status = "WAITING_FOR_FIRST_NEXT_FIXTURE_STATS"
    elif counters["no_next_fixture_known"]:
        status = "WAITING_FOR_NEXT_FIXTURE"
    else:
        status = "NO_NEW_FORWARD_LABELS"

    write_json(
        META,
        {
            "version": VERSION,
            "source_version": SOURCE_VERSION,
            "run_at_utc": run_at,
            "status": status,
            **counters,
            "stats_rows": len(stats_rows),
            "backlog_rows": len(backlog_rows),
            "existing_labels": len(existing_rows),
            "new_labels": len(new_rows),
            "total_labels": len(combined),
            "first_next_match_required": True,
            "later_match_fallback_allowed": False,
            "validation_result_created": False,
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
                "new_labels": len(new_rows),
                "total_labels": len(combined),
                "pending_first_match_stats": counters[
                    "first_next_fixture_stats_pending"
                ],
                "waiting_next_fixture": counters[
                    "no_next_fixture_known"
                ],
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
