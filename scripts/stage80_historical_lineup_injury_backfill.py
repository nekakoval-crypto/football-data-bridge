#!/usr/bin/env python3
"""Stage80 PBK16 historical lineup + adaptive injury backfill.

This stage builds RETROSPECTIVE historical evidence only.

Inputs:
- ops/pbk16_all_competition_fixture_history.csv

Outputs:
- ops/historical_lineup_snapshots.csv
- ops/historical_injury_snapshots.csv
- ops/stage80_historical_lineup_injury_backfill_state.csv
- ops/stage80_historical_lineup_injury_backfill_last_run.json

Provider access:
- only through the shared API-Football broker/budget layer
- successful real provider calls are archived by the shared raw archive layer

Temporal semantics:
- responses retrieved now for historical fixtures are retrospective evidence
- no PREMATCH_FROZEN authority is claimed
- no signal/probability/eligibility/stake/Forward Journal mutation

Policy:
- lineups: attempt all eligible PBK16 domestic league fixtures, newest first
- injuries: adaptive competition-season suppression after repeated exact NO_DATA
- CAPTURED and exact NO_DATA are terminal per fixture+endpoint
- ERROR remains retryable
- first quota marker stops the batch immediately
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
import stage77_player_stats_capture as current
from api_football_broker import ApiFootballBrokerError


OPS = Path(os.getenv("OPS_DIR", "ops"))
SOURCE = OPS / "pbk16_all_competition_fixture_history.csv"
LINEUPS = OPS / "historical_lineup_snapshots.csv"
INJURIES = OPS / "historical_injury_snapshots.csv"
STATE = OPS / "stage80_historical_lineup_injury_backfill_state.csv"
META = OPS / "stage80_historical_lineup_injury_backfill_last_run.json"
BUDGET_STATE = OPS / "stage80_historical_lineup_injury_budget_state.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

VERSION = "PBK_STAGE80_HISTORICAL_LINEUP_INJURY_BACKFILL_V1"
TERMINAL = {"FT", "AET", "PEN", "FINISHED"}
ENDPOINT_LINEUPS = "/fixtures/lineups"
ENDPOINT_INJURIES = "/injuries"

LINEUP_FIELDS = [
    "fixture_id",
    "country",
    "provider_competition_id",
    "competition_name",
    "season",
    "round",
    "kickoff_utc",
    "home_team",
    "away_team",
    "team_id",
    "team_name",
    "side",
    "formation",
    "coach_id",
    "coach_name",
    "starting_xi_json",
    "starting_xi_count",
    "substitutes_json",
    "substitutes_count",
    "retrieved_at_utc",
    "source_endpoint",
    "temporal_authority",
    "archive_version",
]

INJURY_FIELDS = [
    "fixture_id",
    "country",
    "provider_competition_id",
    "competition_name",
    "season",
    "round",
    "kickoff_utc",
    "home_team",
    "away_team",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "availability_type",
    "reason",
    "retrieved_at_utc",
    "source_endpoint",
    "temporal_authority",
    "archive_version",
]

STATE_FIELDS = [
    "fixture_id",
    "endpoint",
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
    "response_rows",
    "normalized_rows",
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
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def season_number(row):
    try:
        return int(sval(row, "season"))
    except ValueError:
        return -1


def domestic_terminal_fixture_map(rows):
    output = {}
    for row in rows:
        fixture_id = sval(row, "fixture_id")
        status = sval(row, "status").upper()
        role = sval(row, "competition_role").upper()
        if not fixture_id or status not in TERMINAL:
            continue
        if "LEAGUE" not in role or "UEFA" in role:
            continue
        output.setdefault(fixture_id, dict(row))
    return output


def state_key(fixture_id, endpoint):
    return (str(fixture_id), str(endpoint))


def read_state(rows):
    output = {}
    for row in rows:
        fixture_id = sval(row, "fixture_id")
        endpoint = sval(row, "endpoint")
        if fixture_id and endpoint:
            output[state_key(fixture_id, endpoint)] = {
                field: row.get(field, "")
                for field in STATE_FIELDS
            }
    return output


def attempt_count(row):
    try:
        return max(0, int(str((row or {}).get("attempt_count") or "0")))
    except ValueError:
        return 0


def competition_season_key(row):
    return (
        sval(row, "provider_competition_id"),
        sval(row, "season"),
    )


def injury_cell_counts(state):
    counts = {}
    for row in state.values():
        if sval(row, "endpoint") != ENDPOINT_INJURIES:
            continue
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


def injury_cell_is_empty(counts, key, threshold):
    bucket = counts.get(key) or {}
    return (
        int(bucket.get("CAPTURED") or 0) == 0
        and int(bucket.get("NO_DATA") or 0) >= threshold
    )


def endpoint_priority(endpoint):
    return 0 if endpoint == ENDPOINT_LINEUPS else 1


def candidate_tasks(history, state, injury_no_data_cell_threshold=8):
    counts = injury_cell_counts(state)
    tasks = []

    for fixture_id, fixture in history.items():
        for endpoint in (ENDPOINT_LINEUPS, ENDPOINT_INJURIES):
            old = state.get(state_key(fixture_id, endpoint)) or {}
            result = sval(old, "last_attempt_result").upper()

            if result in {"CAPTURED", "NO_DATA"}:
                continue

            if (
                endpoint == ENDPOINT_INJURIES
                and injury_cell_is_empty(
                    counts,
                    competition_season_key(fixture),
                    injury_no_data_cell_threshold,
                )
            ):
                continue

            tasks.append((dict(fixture), endpoint))

    tasks.sort(
        key=lambda item: (
            -season_number(item[0]),
            sval(item[0], "country"),
            sval(item[0], "provider_competition_id"),
            sval(item[0], "kickoff_utc"),
            sval(item[0], "fixture_id"),
            endpoint_priority(item[1]),
        )
    )
    return tasks


def normalize_player_list(items):
    output = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        player = item.get("player") if isinstance(item.get("player"), dict) else item
        output.append(
            {
                "id": player.get("id"),
                "name": player.get("name"),
                "number": player.get("number"),
                "pos": player.get("pos") or player.get("position"),
                "grid": player.get("grid"),
            }
        )
    return output


def normalize_lineups(payload, fixture, retrieved_at):
    response = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(response, list):
        raise ValueError("lineup payload response is not a list")

    rows = []
    for team_entry in response:
        if not isinstance(team_entry, dict):
            continue

        team = team_entry.get("team") or {}
        coach = team_entry.get("coach") or {}
        start_xi = normalize_player_list(team_entry.get("startXI") or [])
        substitutes = normalize_player_list(team_entry.get("substitutes") or [])

        team_id = str(team.get("id") or "").strip()
        team_name = str(team.get("name") or "").strip()
        if not team_id and not team_name:
            continue

        home_team = sval(fixture, "home_team")
        away_team = sval(fixture, "away_team")
        side = ""
        if team_name and team_name == home_team:
            side = "HOME"
        elif team_name and team_name == away_team:
            side = "AWAY"

        rows.append(
            {
                "fixture_id": sval(fixture, "fixture_id"),
                "country": sval(fixture, "country"),
                "provider_competition_id": sval(
                    fixture, "provider_competition_id"
                ),
                "competition_name": sval(fixture, "competition_name"),
                "season": sval(fixture, "season"),
                "round": sval(fixture, "round"),
                "kickoff_utc": sval(fixture, "kickoff_utc"),
                "home_team": home_team,
                "away_team": away_team,
                "team_id": team_id,
                "team_name": team_name,
                "side": side,
                "formation": str(team_entry.get("formation") or "").strip(),
                "coach_id": str(coach.get("id") or "").strip(),
                "coach_name": str(coach.get("name") or "").strip(),
                "starting_xi_json": canonical_json(start_xi),
                "starting_xi_count": str(len(start_xi)),
                "substitutes_json": canonical_json(substitutes),
                "substitutes_count": str(len(substitutes)),
                "retrieved_at_utc": retrieved_at,
                "source_endpoint": ENDPOINT_LINEUPS,
                "temporal_authority": "RETROSPECTIVE_ONLY",
                "archive_version": VERSION,
            }
        )
    return rows, len(response)


def normalize_injuries(payload, fixture, retrieved_at):
    response = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(response, list):
        raise ValueError("injury payload response is not a list")

    rows = []
    seen = set()
    for item in response:
        if not isinstance(item, dict):
            continue
        team = item.get("team") or {}
        player = item.get("player") or {}

        row = {
            "fixture_id": sval(fixture, "fixture_id"),
            "country": sval(fixture, "country"),
            "provider_competition_id": sval(
                fixture, "provider_competition_id"
            ),
            "competition_name": sval(fixture, "competition_name"),
            "season": sval(fixture, "season"),
            "round": sval(fixture, "round"),
            "kickoff_utc": sval(fixture, "kickoff_utc"),
            "home_team": sval(fixture, "home_team"),
            "away_team": sval(fixture, "away_team"),
            "team_id": str(team.get("id") or "").strip(),
            "team_name": str(team.get("name") or "").strip(),
            "player_id": str(player.get("id") or "").strip(),
            "player_name": str(player.get("name") or "").strip(),
            "availability_type": str(player.get("type") or "").strip(),
            "reason": str(player.get("reason") or "").strip(),
            "retrieved_at_utc": retrieved_at,
            "source_endpoint": ENDPOINT_INJURIES,
            "temporal_authority": "RETROSPECTIVE_ONLY",
            "archive_version": VERSION,
        }

        dedupe = (
            row["fixture_id"],
            row["team_id"],
            row["player_id"] or row["player_name"],
            row["availability_type"],
            row["reason"],
        )
        if dedupe in seen:
            continue
        seen.add(dedupe)
        rows.append(row)

    return rows, len(response)


def lineup_identity(row):
    return (
        sval(row, "fixture_id"),
        sval(row, "team_id") or sval(row, "team_name"),
    )


def injury_identity(row):
    return (
        sval(row, "fixture_id"),
        sval(row, "team_id"),
        sval(row, "player_id") or sval(row, "player_name"),
        sval(row, "availability_type"),
        sval(row, "reason"),
    )


def merge_rows(existing, new_rows, key_fn):
    merged = {}
    for row in existing:
        key = key_fn(row)
        if all(key):
            merged[key] = dict(row)
    for row in new_rows:
        key = key_fn(row)
        if all(key):
            merged.setdefault(key, dict(row))
    return [merged[key] for key in sorted(merged)]


def state_row_from_task(fixture, endpoint, previous=None):
    previous = previous or {}
    return {
        "fixture_id": sval(fixture, "fixture_id"),
        "endpoint": endpoint,
        "country": sval(fixture, "country"),
        "provider_competition_id": sval(
            fixture, "provider_competition_id"
        ),
        "competition_name": sval(fixture, "competition_name"),
        "season": sval(fixture, "season"),
        "round": sval(fixture, "round"),
        "kickoff_utc": sval(fixture, "kickoff_utc"),
        "home_team": sval(fixture, "home_team"),
        "away_team": sval(fixture, "away_team"),
        "attempt_count": str(attempt_count(previous)),
        "last_attempt_at_utc": previous.get("last_attempt_at_utc", ""),
        "last_attempt_result": previous.get("last_attempt_result", ""),
        "response_rows": previous.get("response_rows", ""),
        "normalized_rows": previous.get("normalized_rows", ""),
        "last_error": previous.get("last_error", ""),
    }


def apply_attempt(
    state,
    fixture,
    endpoint,
    *,
    result,
    attempted_at,
    response_rows=0,
    normalized_rows=0,
    error="",
):
    key = state_key(sval(fixture, "fixture_id"), endpoint)
    old = state.get(key) or {}
    row = state_row_from_task(fixture, endpoint, old)
    row["attempt_count"] = str(attempt_count(old) + 1)
    row["last_attempt_at_utc"] = attempted_at
    row["last_attempt_result"] = result
    row["response_rows"] = str(int(response_rows or 0))
    row["normalized_rows"] = str(int(normalized_rows or 0))
    row["last_error"] = str(error or "")
    state[key] = row


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


def run_capture(
    tasks,
    existing_lineups,
    existing_injuries,
    state,
    get,
    now,
    limit,
    injury_no_data_cell_threshold=8,
):
    lineup_rows = list(existing_lineups)
    injury_rows = list(existing_injuries)
    new_lineups = []
    new_injuries = []

    attempted = 0
    captured = defaultdict(int)
    no_data = defaultdict(int)
    errors = defaultdict(int)
    suppressed_injury_tasks = 0
    quota_exhausted = False
    quota_error = ""
    warnings = []

    counts = injury_cell_counts(state)

    for fixture, endpoint in tasks:
        if attempted >= limit:
            break

        if (
            endpoint == ENDPOINT_INJURIES
            and injury_cell_is_empty(
                counts,
                competition_season_key(fixture),
                injury_no_data_cell_threshold,
            )
        ):
            suppressed_injury_tasks += 1
            continue

        fixture_id = sval(fixture, "fixture_id")
        attempted_at = iso(now)

        try:
            payload = get(
                endpoint,
                {"fixture": fixture_id},
                ttl_seconds=30 * 24 * 3600,
                force_refresh=False,
            )
        except audit.ProtectedBudgetError as exc:
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
            errors[endpoint] += 1
            error_text = f"{type(exc).__name__}: {exc}"
            apply_attempt(
                state,
                fixture,
                endpoint,
                result="ERROR",
                attempted_at=attempted_at,
                error=error_text,
            )
            if is_provider_quota_error(exc):
                quota_exhausted = True
                quota_error = error_text
                warnings.append(
                    "Provider quota exhausted; batch stopped after first quota error."
                )
                break
            continue

        attempted += 1
        retrieved_at = iso(now)

        if endpoint == ENDPOINT_LINEUPS:
            normalized, response_rows = normalize_lineups(
                payload,
                fixture,
                retrieved_at,
            )
        else:
            normalized, response_rows = normalize_injuries(
                payload,
                fixture,
                retrieved_at,
            )

        if response_rows == 0 or not normalized:
            no_data[endpoint] += 1
            apply_attempt(
                state,
                fixture,
                endpoint,
                result="NO_DATA",
                attempted_at=attempted_at,
                response_rows=response_rows,
                normalized_rows=len(normalized),
            )
            if endpoint == ENDPOINT_INJURIES:
                bucket = counts.setdefault(
                    competition_season_key(fixture),
                    {"CAPTURED": 0, "NO_DATA": 0, "ERROR": 0},
                )
                bucket["NO_DATA"] += 1
            continue

        captured[endpoint] += 1
        if endpoint == ENDPOINT_LINEUPS:
            new_lineups.extend(normalized)
        else:
            new_injuries.extend(normalized)
            bucket = counts.setdefault(
                competition_season_key(fixture),
                {"CAPTURED": 0, "NO_DATA": 0, "ERROR": 0},
            )
            bucket["CAPTURED"] += 1

        apply_attempt(
            state,
            fixture,
            endpoint,
            result="CAPTURED",
            attempted_at=attempted_at,
            response_rows=response_rows,
            normalized_rows=len(normalized),
        )

    lineup_rows = merge_rows(
        lineup_rows,
        new_lineups,
        lineup_identity,
    )
    injury_rows = merge_rows(
        injury_rows,
        new_injuries,
        injury_identity,
    )

    return {
        "lineups": lineup_rows,
        "injuries": injury_rows,
        "new_lineup_rows": len(new_lineups),
        "new_injury_rows": len(new_injuries),
        "attempted_tasks": attempted,
        "captured_lineup_tasks": captured[ENDPOINT_LINEUPS],
        "captured_injury_tasks": captured[ENDPOINT_INJURIES],
        "no_data_lineup_tasks": no_data[ENDPOINT_LINEUPS],
        "no_data_injury_tasks": no_data[ENDPOINT_INJURIES],
        "error_lineup_tasks": errors[ENDPOINT_LINEUPS],
        "error_injury_tasks": errors[ENDPOINT_INJURIES],
        "suppressed_injury_tasks": suppressed_injury_tasks,
        "provider_quota_exhausted": quota_exhausted,
        "provider_quota_error": quota_error,
        "warnings": warnings,
    }


def state_totals(state_rows):
    totals = defaultdict(lambda: defaultdict(int))
    for row in state_rows:
        endpoint = sval(row, "endpoint")
        result = sval(row, "last_attempt_result").upper()
        if endpoint and result:
            totals[endpoint][result] += 1
    return {
        endpoint: dict(values)
        for endpoint, values in totals.items()
    }


def main():
    now = datetime.now(timezone.utc)

    source_rows = read_csv(SOURCE)
    existing_lineups = read_csv(LINEUPS)
    existing_injuries = read_csv(INJURIES)
    state = read_state(read_csv(STATE))

    history = domestic_terminal_fixture_map(source_rows)

    injury_no_data_cell_threshold = int(
        os.getenv(
            "STAGE80_HISTORICAL_INJURY_NO_DATA_CELL_THRESHOLD",
            "8",
        )
    )
    max_calls = int(
        os.getenv(
            "STAGE80_HISTORICAL_LINEUP_INJURY_MAX_API_CALLS",
            "600",
        )
    )
    daily_limit = int(
        os.getenv("STAGE71_MAX_DAILY_API_CALLS", "7000")
    )

    tasks_before = candidate_tasks(
        history,
        state,
        injury_no_data_cell_threshold,
    )

    shared_state = audit.read(SHARED_STATE)
    historical_budget_state = audit.read(BUDGET_STATE)
    reserve = current.protected_calls(OPS, now)

    api_day = now.date().isoformat()
    shared_api_day_calls = (
        int(shared_state.get("api_day_calls") or 0)
        if shared_state.get("api_day") == api_day
        else 0
    )
    historical_daily_limit = max(
        0,
        daily_limit - shared_api_day_calls,
    )

    budget = audit.Budget(
        s53.api_get,
        historical_budget_state,
        now,
        limit=max_calls,
        daily_limit=historical_daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(
            BUDGET_STATE,
            value,
        ),
    )

    result = run_capture(
        tasks_before,
        existing_lineups,
        existing_injuries,
        state,
        budget,
        now,
        max_calls,
        injury_no_data_cell_threshold,
    )

    write_csv_atomic(
        LINEUPS,
        LINEUP_FIELDS,
        result["lineups"],
    )
    write_csv_atomic(
        INJURIES,
        INJURY_FIELDS,
        result["injuries"],
    )

    state_rows = [
        state[key]
        for key in sorted(
            state,
            key=lambda key: (
                state[key].get("last_attempt_at_utc", ""),
                key[0],
                key[1],
            ),
        )
    ]
    write_csv_atomic(
        STATE,
        STATE_FIELDS,
        state_rows,
    )
    audit.save(BUDGET_STATE, historical_budget_state)

    tasks_after = candidate_tasks(
        history,
        state,
        injury_no_data_cell_threshold,
    )

    injury_counts = injury_cell_counts(state)
    suppressed_cells = [
        {
            "provider_competition_id": key[0],
            "season": key[1],
            **bucket,
        }
        for key, bucket in sorted(injury_counts.items())
        if injury_cell_is_empty(
            injury_counts,
            key,
            injury_no_data_cell_threshold,
        )
    ]

    meta = {
        "version": VERSION,
        "run_at_utc": iso(now),
        "status": (
            "ATTENTION"
            if result["provider_quota_exhausted"]
            or result["error_lineup_tasks"]
            or result["error_injury_tasks"]
            or result["warnings"]
            else "OK"
        ),
        "source_rows": len(source_rows),
        "terminal_pbk16_domestic_fixtures": len(history),
        "candidate_tasks_before_run": len(tasks_before),
        "attempted_tasks": result["attempted_tasks"],
        "provider_calls": budget.calls,
        "max_provider_calls": max_calls,
        "shared_api_day_calls_at_start": shared_api_day_calls,
        "historical_api_day_calls": historical_budget_state.get(
            "api_day_calls",
            0,
        ),
        "estimated_combined_api_day_calls": (
            shared_api_day_calls
            + int(historical_budget_state.get("api_day_calls") or 0)
        ),
        "historical_daily_limit_after_shared_usage": historical_daily_limit,
        "protected_calls": reserve,
        "captured_lineup_tasks_this_run": result[
            "captured_lineup_tasks"
        ],
        "captured_injury_tasks_this_run": result[
            "captured_injury_tasks"
        ],
        "no_data_lineup_tasks_this_run": result[
            "no_data_lineup_tasks"
        ],
        "no_data_injury_tasks_this_run": result[
            "no_data_injury_tasks"
        ],
        "error_lineup_tasks_this_run": result[
            "error_lineup_tasks"
        ],
        "error_injury_tasks_this_run": result[
            "error_injury_tasks"
        ],
        "suppressed_injury_tasks_this_run": result[
            "suppressed_injury_tasks"
        ],
        "new_lineup_rows": result["new_lineup_rows"],
        "new_injury_rows": result["new_injury_rows"],
        "total_lineup_rows": len(result["lineups"]),
        "total_injury_rows": len(result["injuries"]),
        "state_rows": len(state_rows),
        "state_totals": state_totals(state_rows),
        "injury_no_data_cell_threshold": injury_no_data_cell_threshold,
        "suppressed_injury_cells": suppressed_cells,
        "remaining_candidate_tasks": len(tasks_after),
        "provider_quota_exhausted": result[
            "provider_quota_exhausted"
        ],
        "provider_quota_error": result[
            "provider_quota_error"
        ],
        "warnings": result["warnings"],
        "lineup_policy": (
            "ALL_PBK16_DOMESTIC_TERMINAL_FIXTURES;"
            "NEWEST_SEASON_FIRST;FIXTURE_INTERLEAVED_WITH_INJURIES"
        ),
        "injury_policy": (
            "ADAPTIVE_COMPETITION_SEASON_SUPPRESSION;"
            "SUPPRESS_AFTER_ZERO_CAPTURE_AND_NO_DATA_THRESHOLD"
        ),
        "historical_no_data_is_terminal_per_fixture_endpoint": True,
        "raw_archive_via_shared_broker": True,
        "retrospective_reconstructed": True,
        "temporal_authority": "RETROSPECTIVE_ONLY",
        "pre_match_observation_time_known": False,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }

    META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()