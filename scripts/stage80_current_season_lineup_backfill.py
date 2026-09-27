#!/usr/bin/env python3
"""PBK Point14 V25 — current-season lineup convergence.

Purpose:
- prioritize current-season PBK16 domestic terminal fixtures;
- lineups only, no injury polling;
- newest fixtures first;
- reuse the existing historical lineup state/output and shared API budget;
- archive-first through the shared API-Football broker;
- provider calls only for still-missing current-season lineup fixtures.

This is retrospective lineup evidence for hierarchy/Expected-XI research.
No betting authority and no PREMATCH_FROZEN claim.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone

import stage53_daily_screener as s53
import stage71_observation_audit as audit
import stage77_player_stats_capture as current
import stage80_historical_lineup_injury_backfill as base

OPS = base.OPS
SOURCE = base.SOURCE
LINEUPS = base.LINEUPS
INJURIES = base.INJURIES
STATE = base.STATE
BUDGET_STATE = base.BUDGET_STATE
SHARED_STATE = base.SHARED_STATE
META = OPS / "stage80_current_season_lineup_backfill_last_run.json"

VERSION = "PBK_STAGE80_CURRENT_SEASON_LINEUP_CONVERGENCE_V1"


def current_season_number(history):
    values = [base.season_number(row) for row in history.values()]
    values = [v for v in values if v >= 0]
    return max(values) if values else -1


def current_season_lineup_tasks(history, state, season):
    tasks = []
    for fixture_id, fixture in history.items():
        if base.season_number(fixture) != int(season):
            continue

        old = state.get(base.state_key(fixture_id, base.ENDPOINT_LINEUPS)) or {}
        result = base.sval(old, "last_attempt_result").upper()
        if result in {"CAPTURED", "NO_DATA"}:
            continue

        tasks.append((dict(fixture), base.ENDPOINT_LINEUPS))

    tasks.sort(
        key=lambda item: (
            base.sval(item[0], "kickoff_utc"),
            base.sval(item[0], "fixture_id"),
        ),
        reverse=True,
    )
    return tasks


def captured_fixture_ids(state, season):
    result = set()
    for row in state.values():
        if base.sval(row, "endpoint") != base.ENDPOINT_LINEUPS:
            continue
        if base.season_number(row) != int(season):
            continue
        if base.sval(row, "last_attempt_result").upper() == "CAPTURED":
            fid = base.sval(row, "fixture_id")
            if fid:
                result.add(fid)
    return result


def complete_team_rows(lineup_rows, season):
    counts = Counter()
    for row in lineup_rows:
        if base.season_number(row) != int(season):
            continue
        try:
            xi_count = int(base.sval(row, "starting_xi_count") or "0")
        except ValueError:
            xi_count = 0
        if xi_count != 11:
            continue
        tid = base.sval(row, "team_id")
        if tid:
            counts[tid] += 1
    return counts


def main():
    now = datetime.now(timezone.utc)

    source_rows = base.read_csv(SOURCE)
    existing_lineups = base.read_csv(LINEUPS)
    existing_injuries = base.read_csv(INJURIES)
    state = base.read_state(base.read_csv(STATE))

    history = base.domestic_terminal_fixture_map(source_rows)
    season = current_season_number(history)

    tasks_before = current_season_lineup_tasks(history, state, season)
    captured_before = captured_fixture_ids(state, season)

    max_calls = int(os.getenv("STAGE80_CURRENT_SEASON_LINEUP_MAX_API_CALLS", "240"))
    daily_limit = int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "7000"))
    provider_timeout_seconds = int(os.getenv("STAGE80_PROVIDER_CALL_TIMEOUT_SECONDS", "45"))
    heartbeat_every = int(os.getenv("STAGE80_HEARTBEAT_EVERY_TASKS", "10"))
    max_consecutive_errors = int(os.getenv("STAGE80_MAX_CONSECUTIVE_PROVIDER_ERRORS", "5"))
    checkpoint_every = int(os.getenv("STAGE80_CHECKPOINT_EVERY_TASKS", "25"))

    shared_state = audit.read(SHARED_STATE)
    budget_state = audit.read(BUDGET_STATE)
    reserve = current.protected_calls(OPS, now)

    api_day = now.date().isoformat()
    shared_calls = (
        int(shared_state.get("api_day_calls") or 0)
        if shared_state.get("api_day") == api_day
        else 0
    )
    historical_daily_limit = max(0, daily_limit - shared_calls)

    budget = audit.Budget(
        s53.api_get,
        budget_state,
        now,
        limit=max_calls,
        daily_limit=historical_daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(BUDGET_STATE, value),
    )

    def persist_checkpoint(state_map, lineup_rows_checkpoint, injury_rows_checkpoint):
        base.write_csv_atomic(LINEUPS, base.LINEUP_FIELDS, lineup_rows_checkpoint)
        base.write_csv_atomic(INJURIES, base.INJURY_FIELDS, injury_rows_checkpoint)

        state_rows_checkpoint = [
            state_map[key]
            for key in sorted(
                state_map,
                key=lambda key: (
                    state_map[key].get("last_attempt_at_utc", ""),
                    key[0],
                    key[1],
                ),
            )
        ]
        base.write_csv_atomic(STATE, base.STATE_FIELDS, state_rows_checkpoint)
        audit.save(BUDGET_STATE, budget_state)

    result = base.run_capture(
        tasks_before,
        existing_lineups,
        existing_injuries,
        state,
        budget,
        now,
        max_calls,
        provider_timeout_seconds=provider_timeout_seconds,
        heartbeat_every=heartbeat_every,
        max_consecutive_errors=max_consecutive_errors,
        checkpoint_every=checkpoint_every,
        checkpoint=persist_checkpoint,
    )

    base.write_csv_atomic(LINEUPS, base.LINEUP_FIELDS, result["lineups"])
    base.write_csv_atomic(INJURIES, base.INJURY_FIELDS, result["injuries"])

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
    base.write_csv_atomic(STATE, base.STATE_FIELDS, state_rows)
    audit.save(BUDGET_STATE, budget_state)

    tasks_after = current_season_lineup_tasks(history, state, season)
    captured_after = captured_fixture_ids(state, season)
    complete_counts = complete_team_rows(result["lineups"], season)

    current_season_fixture_count = sum(
        1 for row in history.values() if base.season_number(row) == int(season)
    )

    meta = {
        "version": VERSION,
        "run_at_utc": base.iso(now),
        "status": (
            "ATTENTION"
            if result["provider_quota_exhausted"]
            or result["error_lineup_tasks"]
            or result["warnings"]
            else "OK"
        ),
        "season": season,
        "source_rows": len(source_rows),
        "current_season_terminal_domestic_fixtures": current_season_fixture_count,
        "captured_current_season_lineup_fixtures_before": len(captured_before),
        "captured_current_season_lineup_fixtures_after": len(captured_after),
        "missing_current_season_lineup_tasks_before": len(tasks_before),
        "missing_current_season_lineup_tasks_after": len(tasks_after),
        "attempted_tasks": result["attempted_tasks"],
        "provider_calls": budget.calls,
        "max_provider_calls": max_calls,
        "captured_lineup_tasks_this_run": result["captured_lineup_tasks"],
        "no_data_lineup_tasks_this_run": result["no_data_lineup_tasks"],
        "error_lineup_tasks_this_run": result["error_lineup_tasks"],
        "new_lineup_rows": result["new_lineup_rows"],
        "provider_quota_exhausted": result["provider_quota_exhausted"],
        "warnings": result["warnings"],
        "complete_current_season_lineup_rows_by_focus_team": {
            "33": complete_counts.get("33", 0),
            "47": complete_counts.get("47", 0),
        },
        "task_policy": (
            "CURRENT_MAX_SEASON_ONLY;"
            "DOMESTIC_TERMINAL;"
            "LINEUPS_ONLY;"
            "NEWEST_KICKOFF_FIRST;"
            "NO_TEAM_SPECIFIC_SELECTION_EXCEPTION"
        ),
        "archive_first_enabled": True,
        "shared_state_reused": True,
        "shared_budget_reused": True,
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
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print("POINT14 CURRENT-SEASON LINEUP CONVERGENCE V25 PASSED")


if __name__ == "__main__":
    main()
