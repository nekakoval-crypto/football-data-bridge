#!/usr/bin/env python3
"""PBK #292 — bounded historical team-statistics backfill for environment research.

Seeds durable Stage81 backlog from the already-verified PBK14 fixture bridge and
captures API-Football /fixtures/statistics through the shared broker/budget.

Scope is intentionally narrow:
- AUTO/HIGH bridge rows only;
- one-to-one verified identity only;
- no fuzzy matching;
- seasons from 2022 onward by default, matching Historical Forecast coverage;
- home team must exist in the PBK16 venue registry;
- research/archive only, no model or betting authority.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
import stage81_team_match_statistics_capture as s81

OPS = Path(os.getenv("OPS_DIR", "ops"))
BRIDGE = OPS / "pbk14_football_data_fixture_bridge.csv"
VENUES = OPS / "pbk16_venue_registry.csv"
LEDGER = OPS / "team_match_statistics.csv"
BACKLOG = OPS / "stage81_team_stats_backlog.csv"
SHARED_STATE = OPS / "stage71_observation_state.json"
META = OPS / "stage292_environmental_historical_backfill_last_run.json"
MARKETS = Path(
    os.getenv(
        "STAGE292_MARKETS_PATH",
        "normalized/football_data_pbk14_9season_matches.csv",
    )
)

MIN_SEASON = int(os.getenv("STAGE292_MIN_SEASON", "2022"))
MAX_API_CALLS = int(os.getenv("STAGE292_MAX_API_CALLS", "96"))
MAX_FIXTURES_PER_RUN = int(
    os.getenv("STAGE292_MAX_FIXTURES_PER_RUN", str(MAX_API_CALLS))
)


def read_csv(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def as_int(value):
    try:
        return int(float(str(value or "").strip()))
    except (TypeError, ValueError):
        return None


def as_float(value):
    try:
        return float(str(value or "").strip())
    except (TypeError, ValueError):
        return None


def valid_odds_pair(a, b):
    x = as_float(a)
    y = as_float(b)
    return x is not None and y is not None and x > 1 and y > 1


def market_ou25_historical_ids(rows):
    out = set()
    for row in rows:
        historical_match_id = str(row.get("historical_match_id") or "").strip()
        if not historical_match_id:
            continue
        if valid_odds_pair(
            row.get("avg_close_over_25"),
            row.get("avg_close_under_25"),
        ) or valid_odds_pair(
            row.get("b365_close_over_25"),
            row.get("b365_close_under_25"),
        ):
            out.add(historical_match_id)
    return out


def trusted_bridge_fixture(
    row,
    venue_team_ids,
    min_season,
    market_historical_ids=None,
):
    fixture_id = str(row.get("api_fixture_id") or "").strip()
    historical_match_id = str(row.get("historical_match_id") or "").strip()
    kickoff = str(row.get("api_kickoff_utc") or "").strip()
    season = as_int(row.get("season_start"))
    home_team_id = str(row.get("api_home_team_id") or "").strip()
    mapping = str(row.get("mapping_status") or "").strip().upper()
    one_to_one = str(row.get("one_to_one_verified") or "").strip().lower()
    fuzzy = str(row.get("fuzzy_string_matching_used") or "").strip().lower()

    if (
        not fixture_id
        or not kickoff
        or season is None
        or season < min_season
        or mapping not in {"AUTO", "HIGH"}
        or one_to_one != "true"
        or fuzzy != "false"
        or home_team_id not in venue_team_ids
        or (
            market_historical_ids is not None
            and historical_match_id not in market_historical_ids
        )
    ):
        return None

    return {
        "fixture_id": fixture_id,
        "provider_league_id": str(row.get("provider_league_id") or "").strip(),
        "league_name": str(row.get("league_code") or "").strip(),
        "season": str(season),
        "round": "HISTORICAL_BRIDGE",
        "kickoff_utc": kickoff,
        "home_team": str(
            row.get("api_home_team") or row.get("source_home_team") or ""
        ).strip(),
        "away_team": str(
            row.get("api_away_team") or row.get("source_away_team") or ""
        ).strip(),
        "source_status": "FT",
        "status": "FINISHED",
    }


def eligible_bridge_fixtures(
    bridge_rows,
    venue_rows,
    min_season=MIN_SEASON,
    market_historical_ids=None,
):
    venue_team_ids = {
        str(row.get("team_id") or "").strip()
        for row in venue_rows
        if str(row.get("team_id") or "").strip()
    }
    fixtures = []
    seen = set()

    for row in bridge_rows:
        fixture = trusted_bridge_fixture(
            row,
            venue_team_ids,
            min_season,
            market_historical_ids,
        )
        if not fixture:
            continue
        fixture_id = fixture["fixture_id"]
        if fixture_id in seen:
            continue
        seen.add(fixture_id)
        fixtures.append(fixture)

    fixtures.sort(
        key=lambda row: (
            str(row.get("kickoff_utc") or ""),
            str(row.get("fixture_id") or ""),
        )
    )
    return fixtures


def main():
    now = datetime.now(timezone.utc)
    bridge_rows = read_csv(BRIDGE)
    venue_rows = read_csv(VENUES)
    market_rows = read_csv(MARKETS)
    if not market_rows:
        raise RuntimeError(f"Stage292 market baseline missing or empty: {MARKETS}")
    market_ids = market_ou25_historical_ids(market_rows)
    existing_rows = read_csv(LEDGER)
    existing_backlog = read_csv(BACKLOG)

    historical_fixtures = eligible_bridge_fixtures(
        bridge_rows,
        venue_rows,
        MIN_SEASON,
        market_ids,
    )
    historical_ids = {
        str(row.get("fixture_id") or "").strip()
        for row in historical_fixtures
    }

    backlog_before = s81.sync_backlog(
        existing_backlog,
        historical_fixtures,
        existing_rows,
        now,
    )

    # Keep this rail isolated from ordinary current-round Stage81 backlog.
    historical_queue = [
        row
        for row in backlog_before["rows"]
        if str(row.get("fixture_id") or "").strip() in historical_ids
    ]

    state = audit.read(SHARED_STATE)
    reserve = s81.protected_calls(OPS, now)
    daily_limit = int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "7000"))

    budget = audit.Budget(
        s53.api_get,
        state,
        now,
        limit=MAX_API_CALLS,
        daily_limit=daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(SHARED_STATE, value),
    )

    result = s81.capture(
        historical_queue,
        existing_rows,
        budget,
        now,
        MAX_FIXTURES_PER_RUN,
    )

    attempted_backlog = s81.record_attempts(
        backlog_before["rows"],
        result["attempts"],
    )
    backlog_after = s81.sync_backlog(
        attempted_backlog,
        [],
        result["rows"],
        now,
    )

    s81.write_csv_atomic(
        LEDGER,
        s81.LEDGER_FIELDS,
        result["rows"],
    )
    s81.write_csv_atomic(
        BACKLOG,
        s81.BACKLOG_FIELDS,
        backlog_after["rows"],
    )
    audit.save(SHARED_STATE, state)

    completed = s81.completed_fixture_ids(result["rows"])
    historical_completed = len(completed & historical_ids)
    historical_pending = sum(
        str(row.get("fixture_id") or "").strip() in historical_ids
        and str(row.get("backlog_status") or "").strip().upper() == "PENDING"
        for row in backlog_after["rows"]
    )

    meta = {
        "version": "PBK_STAGE292_ENVIRONMENTAL_HISTORICAL_BACKFILL_V1",
        "run_at_utc": s81.iso(now),
        "status": "ATTENTION" if result["warnings"] else "OK",
        "min_season": MIN_SEASON,
        "bridge_rows": len(bridge_rows),
        "venue_registry_rows": len(venue_rows),
        "market_rows": len(market_rows),
        "market_ou25_historical_ids": len(market_ids),
        "market_ou25_required": True,
        "eligible_bridge_fixtures": len(historical_fixtures),
        "historical_completed_fixtures": historical_completed,
        "historical_pending_fixtures": historical_pending,
        "provider_calls": budget.calls,
        "attempted_fixtures": len(result["attempts"]),
        "captured_fixtures_this_run": result["captured_fixtures"],
        "captured_fixture_ids": result["captured_fixture_ids"],
        "new_team_stat_rows": result["new_rows"],
        "total_team_stat_rows": len(result["rows"]),
        "deferred_fixtures": result["deferred_fixtures"],
        "protected_calls": reserve,
        "daily_api_calls": state.get("api_day_calls", 0),
        "identity_policy": {
            "mapping_statuses": ["AUTO", "HIGH"],
            "one_to_one_verified_required": True,
            "fuzzy_string_matching_used": False,
            "home_team_in_pbk16_venue_registry_required": True,
            "closing_ou25_required": True,
        },
        "weather_scope_reason": (
            "Historical Forecast coverage starts around 2022; older seasons "
            "are excluded from this rail by default."
        ),
        "research_only": True,
        "historical_backfill_only": True,
        "predictive_authority": "NOT_AUTHORIZED",
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "warnings": result["warnings"],
    }

    META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
