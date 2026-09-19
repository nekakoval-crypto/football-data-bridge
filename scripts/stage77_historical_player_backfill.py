#!/usr/bin/env python3
"""PBK Stage77 historical player-stat / Player Grade backfill.

Consumes the already persisted PBK16 historical fixture archive and asks
API-Football for /fixtures/players only for terminal fixtures that are not
already represented in PBK player-stat + Player Grade ledgers.

Successful real provider responses travel through the existing shared broker,
therefore production R2/S3 raw archival remains active when configured.

Historical EMPTY responses are persisted as NO_DATA and are not polled again.
Transport/runtime failures remain retryable.

Research/archive only. No probability, eligibility, signal, stake or Forward
mutation.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
import stage77_player_stats_capture as current
from api_football_broker import ApiFootballBrokerError


OPS = Path(os.getenv("OPS_DIR", "ops"))

SOURCE = OPS / "pbk16_all_competition_fixture_history.csv"
STATS = OPS / "player_stats_snapshots.csv"
GRADES = OPS / "player_grade_snapshots.csv"
STATE = OPS / "stage77_historical_player_backfill_state.csv"
META = OPS / "stage77_historical_player_backfill_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

VERSION = "PBK_STAGE77_HISTORICAL_PLAYER_BACKFILL_V2"
TERMINAL = {"FT", "AET", "PEN", "FINISHED"}

STATE_FIELDS = [
    "fixture_id",
    "competition_role",
    "country",
    "provider_competition_id",
    "competition_name",
    "season",
    "round",
    "kickoff_utc",
    "home_team",
    "away_team",
    "attempt_count",
    "last_attempt_at_utc",
    "last_attempt_result",
    "player_rows",
    "last_error",
]


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def read_csv(path):
    if not path.exists():
        return []

    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv_atomic(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    temp = path.with_suffix(path.suffix + ".tmp")

    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    temp.replace(path)


def completed_fixture_ids(stats, grades):
    return current.completed_fixture_ids(stats, grades)


def historical_fixture_map(rows):
    output = {}

    for row in rows:
        fixture_id = sval(row, "fixture_id")
        status = sval(row, "status").upper()

        if not fixture_id or status not in TERMINAL:
            continue

        # One historical fixture identity per provider fixture_id.
        # First persisted PBK archive observation wins for queue metadata.
        output.setdefault(fixture_id, dict(row))

    return output


def read_state(rows):
    output = {}

    for row in rows:
        fixture_id = sval(row, "fixture_id")

        if fixture_id:
            output[fixture_id] = {
                field: row.get(field, "")
                for field in STATE_FIELDS
            }

    return output


def attempt_count(row):
    try:
        return max(
            0,
            int(str((row or {}).get("attempt_count") or "0")),
        )
    except ValueError:
        return 0


def role_priority(row):
    role = sval(row, "competition_role").upper()
    comp = sval(row, "competition_name").upper()

    if "DOMESTIC" in role and "LEAGUE" in role:
        return 0

    if role == "LEAGUE":
        return 0

    if "UEFA" in role or "UEFA" in comp:
        return 1

    if "CUP" in role or "CUP" in comp:
        return 2

    return 3


def season_number(row):
    try:
        return int(sval(row, "season"))
    except ValueError:
        return -1


def competition_season_key(row):
    return (
        sval(row, "provider_competition_id"),
        sval(row, "season"),
    )


def cell_observation_counts(state):
    counts = {}

    for row in state.values():
        key = competition_season_key(row)

        if not key[0] or not key[1]:
            continue

        bucket = counts.setdefault(
            key,
            {"CAPTURED": 0, "NO_DATA": 0, "ERROR": 0},
        )

        result = sval(row, "last_attempt_result").upper()

        if result in bucket:
            bucket[result] += 1

    return counts


def cell_is_provider_empty(counts, key, threshold):
    bucket = counts.get(key) or {}

    return (
        int(bucket.get("CAPTURED") or 0) == 0
        and int(bucket.get("NO_DATA") or 0) >= threshold
    )


def cell_evidence_priority(row, counts):
    bucket = counts.get(competition_season_key(row)) or {}

    if int(bucket.get("CAPTURED") or 0) > 0:
        return 0

    return 1


def candidate_rows(history, captured, state,
                   no_data_cell_threshold=8):
    candidates = []
    counts = cell_observation_counts(state)

    for fixture_id, row in history.items():

        if fixture_id in captured:
            continue

        old = state.get(fixture_id) or {}
        result = sval(old, "last_attempt_result").upper()

        # Historical DATA already appears in normalized ledgers.
        # Exact EMPTY evidence remains final for that fixture.
        if result in {"CAPTURED", "NO_DATA"}:
            continue

        if cell_is_provider_empty(
            counts,
            competition_season_key(row),
            no_data_cell_threshold,
        ):
            continue

        candidates.append(dict(row))

    candidates.sort(
        key=lambda row: (
            role_priority(row),
            cell_evidence_priority(row, counts),
            -season_number(row),
            sval(row, "kickoff_utc"),
            sval(row, "country"),
            sval(row, "competition_name"),
            sval(row, "fixture_id"),
        )
    )

    return candidates


def is_provider_quota_error(exc):
    text = str(exc).lower()

    return any(
        marker in text
        for marker in (
            "request limit for the day",
            "http 429",
            "too many requests",
            "rate limit",
        )
    )


def state_row_from_fixture(fixture, previous=None):
    previous = previous or {}

    return {
        "fixture_id": sval(fixture, "fixture_id"),
        "competition_role": sval(fixture, "competition_role"),
        "country": sval(fixture, "country"),
        "provider_competition_id": sval(
            fixture,
            "provider_competition_id",
        ),
        "competition_name": sval(fixture, "competition_name"),
        "season": sval(fixture, "season"),
        "round": sval(fixture, "round"),
        "kickoff_utc": sval(fixture, "kickoff_utc"),
        "home_team": sval(fixture, "home_team"),
        "away_team": sval(fixture, "away_team"),
        "attempt_count": str(attempt_count(previous)),
        "last_attempt_at_utc": previous.get(
            "last_attempt_at_utc",
            "",
        ),
        "last_attempt_result": previous.get(
            "last_attempt_result",
            "",
        ),
        "player_rows": previous.get("player_rows", ""),
        "last_error": previous.get("last_error", ""),
    }


def apply_attempt(state, fixture, *, result, attempted_at,
                  player_rows=0, error=""):
    fixture_id = sval(fixture, "fixture_id")
    old = state.get(fixture_id) or {}

    row = state_row_from_fixture(fixture, old)
    row["attempt_count"] = str(attempt_count(old) + 1)
    row["last_attempt_at_utc"] = attempted_at
    row["last_attempt_result"] = result
    row["player_rows"] = str(int(player_rows or 0))
    row["last_error"] = str(error or "")

    state[fixture_id] = row


def run_capture(candidates, existing_stats, existing_grades,
                state, get, now, limit,
                no_data_cell_threshold=8):

    stats = list(existing_stats)
    grades = list(existing_grades)

    new_stats = []
    new_grades = []

    attempted = 0
    captured = 0
    no_data = 0
    errors = 0
    deferred = 0
    suppressed = 0
    quota_exhausted = False
    quota_error = ""
    warnings = []

    counts = cell_observation_counts(state)

    for index, fixture in enumerate(candidates):

        if attempted >= limit:
            break

        key = competition_season_key(fixture)

        if cell_is_provider_empty(
            counts,
            key,
            no_data_cell_threshold,
        ):
            suppressed += 1
            continue

        fixture_id = sval(fixture, "fixture_id")
        attempted_at = iso(now)

        try:
            payload = get(
                "/fixtures/players",
                {"fixture": fixture_id},
                ttl_seconds=30 * 24 * 3600,
                force_refresh=False,
            )

        except audit.ProtectedBudgetError as exc:
            deferred = max(
                0,
                min(
                    limit - attempted,
                    len(candidates) - index,
                ),
            )
            warnings.append(str(exc))
            break

        except (
            ApiFootballBrokerError,
            RuntimeError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            attempted += 1
            errors += 1

            error_text = f"{type(exc).__name__}: {exc}"

            apply_attempt(
                state,
                fixture,
                result="ERROR",
                attempted_at=attempted_at,
                error=error_text,
            )

            counts.setdefault(
                key,
                {"CAPTURED": 0, "NO_DATA": 0, "ERROR": 0},
            )["ERROR"] += 1

            if is_provider_quota_error(exc):
                quota_exhausted = True
                quota_error = error_text
                deferred = max(
                    0,
                    min(
                        limit - attempted,
                        len(candidates) - index - 1,
                    ),
                )
                warnings.append(
                    "Provider quota exhausted; batch stopped "
                    "after first quota error."
                )
                break

            continue

        attempted += 1

        observed = iso(now)

        stat_rows, grade_rows = current.normalize_fixture_players(
            payload,
            fixture,
            observed,
        )

        bucket = counts.setdefault(
            key,
            {"CAPTURED": 0, "NO_DATA": 0, "ERROR": 0},
        )

        if not stat_rows:
            no_data += 1
            bucket["NO_DATA"] += 1

            apply_attempt(
                state,
                fixture,
                result="NO_DATA",
                attempted_at=attempted_at,
                player_rows=0,
            )

            continue

        captured += 1
        bucket["CAPTURED"] += 1
        new_stats.extend(stat_rows)
        new_grades.extend(grade_rows)

        apply_attempt(
            state,
            fixture,
            result="CAPTURED",
            attempted_at=attempted_at,
            player_rows=len(stat_rows),
        )

    stats = current.merge_rows(stats, new_stats)
    grades = current.merge_rows(grades, new_grades)

    return {
        "stats": stats,
        "grades": grades,
        "new_stats_rows": len(new_stats),
        "new_grade_rows": len(new_grades),
        "attempted_fixtures": attempted,
        "captured_fixtures": captured,
        "no_data_fixtures": no_data,
        "error_fixtures": errors,
        "deferred_fixtures": deferred,
        "suppressed_empty_cell_fixtures": suppressed,
        "provider_quota_exhausted": quota_exhausted,
        "provider_quota_error": quota_error,
        "warnings": warnings,
    }


def main():
    now = datetime.now(timezone.utc)

    source_rows = read_csv(SOURCE)
    existing_stats = read_csv(STATS)
    existing_grades = read_csv(GRADES)
    state_rows = read_csv(STATE)

    history = historical_fixture_map(source_rows)
    state = read_state(state_rows)

    captured_before = completed_fixture_ids(
        existing_stats,
        existing_grades,
    )

    no_data_cell_threshold = int(
        os.getenv(
            "STAGE77_HISTORICAL_NO_DATA_CELL_THRESHOLD",
            "8",
        )
    )

    candidates = candidate_rows(
        history,
        captured_before,
        state,
        no_data_cell_threshold,
    )

    shared_state = audit.read(SHARED_STATE)
    reserve = current.protected_calls(OPS, now)

    max_calls = int(
        os.getenv(
            "STAGE77_HISTORICAL_MAX_API_CALLS",
            "120",
        )
    )

    daily_limit = int(
        os.getenv(
            "STAGE71_MAX_DAILY_API_CALLS",
            "7000",
        )
    )

    budget = audit.Budget(
        s53.api_get,
        shared_state,
        now,
        limit=max_calls,
        daily_limit=daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(
            SHARED_STATE,
            value,
        ),
    )

    result = run_capture(
        candidates,
        existing_stats,
        existing_grades,
        state,
        budget,
        now,
        max_calls,
        no_data_cell_threshold,
    )

    captured_after = completed_fixture_ids(
        result["stats"],
        result["grades"],
    )

    if result["stats"] or STATS.exists():
        current.write_csv_atomic(
            STATS,
            current.STAT_FIELDS,
            result["stats"],
        )

    if result["grades"] or GRADES.exists():
        current.write_csv_atomic(
            GRADES,
            current.GRADE_FIELDS,
            result["grades"],
        )

    state_output = [
        state[key]
        for key in sorted(
            state,
            key=lambda key: (
                state[key].get("last_attempt_at_utc", ""),
                key,
            ),
        )
    ]

    write_csv_atomic(
        STATE,
        STATE_FIELDS,
        state_output,
    )

    audit.save(
        SHARED_STATE,
        shared_state,
    )

    no_data_total = sum(
        sval(row, "last_attempt_result").upper() == "NO_DATA"
        for row in state_output
    )

    error_total = sum(
        sval(row, "last_attempt_result").upper() == "ERROR"
        for row in state_output
    )

    captured_state_total = sum(
        sval(row, "last_attempt_result").upper() == "CAPTURED"
        for row in state_output
    )

    remaining = len(
        candidate_rows(
            history,
            captured_after,
            state,
            no_data_cell_threshold,
        )
    )

    meta = {
        "version": VERSION,
        "run_at_utc": iso(now),
        "status": (
            "ATTENTION"
            if result["error_fixtures"] or result["warnings"]
            else "OK"
        ),
        "provider_endpoint": "/fixtures/players",
        "provider_calls": budget.calls,
        "daily_api_calls": shared_state.get(
            "api_day_calls",
            0,
        ),
        "protected_calls": reserve,
        "pbk16_source_rows": len(source_rows),
        "terminal_historical_fixtures": len(history),
        "normalized_player_fixtures_before": len(
            captured_before
        ),
        "candidate_fixtures_before_run": len(candidates),
        "attempted_fixtures": result["attempted_fixtures"],
        "captured_fixtures_this_run": result[
            "captured_fixtures"
        ],
        "no_data_fixtures_this_run": result[
            "no_data_fixtures"
        ],
        "error_fixtures_this_run": result[
            "error_fixtures"
        ],
        "deferred_fixtures": result[
            "deferred_fixtures"
        ],
        "suppressed_empty_cell_fixtures": result[
            "suppressed_empty_cell_fixtures"
        ],
        "provider_quota_exhausted": result[
            "provider_quota_exhausted"
        ],
        "provider_quota_error": result[
            "provider_quota_error"
        ],
        "no_data_cell_threshold": no_data_cell_threshold,
        "new_stats_rows": result["new_stats_rows"],
        "new_grade_rows": result["new_grade_rows"],
        "total_stats_rows": len(result["stats"]),
        "total_grade_rows": len(result["grades"]),
        "normalized_player_fixtures_after": len(
            captured_after
        ),
        "state_rows": len(state_output),
        "state_captured": captured_state_total,
        "state_no_data": no_data_total,
        "state_error": error_total,
        "remaining_unattempted_or_retryable": remaining,
        "historical_no_data_is_terminal": True,
        "priority_policy": (
            "DOMESTIC_LEAGUE_THEN_UEFA_THEN_CUPS;"
            "PRODUCTIVE_CELL_FIRST;"
            "NEWEST_SEASON_FIRST;"
            "EMPTY_CELL_SUPPRESSION"
        ),
        "warnings": result["warnings"],
        "historical_backfill_only": True,
        "raw_archive_via_shared_broker": True,
        "research_only": True,
        "operational_betting_authority": False,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }

    META.write_text(
        json.dumps(
            meta,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            meta,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
