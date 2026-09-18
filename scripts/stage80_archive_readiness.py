#!/usr/bin/env python3
"""Stage80 — provider-free archive readiness and coverage board.

This is a telemetry/governance layer for the PBK Historical Data Archive. It
reads already-persisted operational/archive evidence, makes no provider calls and
never changes betting/model state. Missing sources are reported explicitly rather
than converted to zeros that look like complete coverage.
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
OUT_JSON = OPS / "stage80_archive_readiness.json"
OUT_MD = OPS / "stage80_archive_readiness.md"
VERSION = "PBK_STAGE80_ARCHIVE_READINESS_V9_STATSBOMB_PLAYER_XG_XA"

SOURCES = {
    "fixtures": "current_round_fixtures.csv",
    "fixture_history": "fixture_history_snapshots.csv",
    "historical_fixtures": "historical_fixtures.csv",
    "player_stats": "player_stats_snapshots.csv",
    "player_grades": "player_grade_snapshots.csv",
    "stage77_backlog": "stage77_player_stats_backlog.csv",
    "team_stats": "team_match_statistics.csv",
    "stage81_backlog": "stage81_team_stats_backlog.csv",
    "current_rosters": "team_rosters.csv",
    "roster_history": "team_roster_history.csv",
    "membership_intervals": "team_membership_intervals.csv",
    "transfer_history": "historical_transfer_events.csv",
    "match_context": "match_context_snapshots.csv",
    "lineup_archive": "lineup_snapshots.csv",
    "injury_archive": "injury_snapshots.csv",
    "match_events": "match_event_snapshots.csv",
    "match_event_backlog": "stage80_match_event_backlog.csv",
    "player_xg_xa_research": "statsbomb_player_xg_xa.csv",
}
FINAL_PROVIDER_CODES = {"FT", "AET", "PEN"}
FINAL_NORMALIZED = {"finished", "ft", "aet", "pen"}
TRUE_VALUES = {"1", "true", "yes", "y"}


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def uniq(rows, key):
    if rows is None:
        return None
    return len({sval(row, key) for row in rows if sval(row, key)})


def pct(num, den):
    if den in (None, 0):
        return None
    return round(100.0 * num / den, 2)


def fnum(value):
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def is_finished_fixture(row):
    return sval(row, "source_status").upper() in FINAL_PROVIDER_CODES or sval(row, "status").lower() in FINAL_NORMALIZED


def is_true(value):
    return str(value or "").strip().lower() in TRUE_VALUES


def raw_archive_inventory(archive_dir=None, ops=OPS):
    configured = archive_dir is not None and str(archive_dir).strip() != ""
    if not configured:
        raw = os.getenv("API_FOOTBALL_ARCHIVE_DIR", "").strip()
        archive_dir = Path(raw) if raw else None
        configured = archive_dir is not None
    else:
        archive_dir = Path(archive_dir)

    verify_path = Path(ops) / "stage80_raw_archive_storage_last_run.json"
    verify = None
    if verify_path.exists():
        try:
            verify = json.loads(verify_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            verify = {"status": "INVALID_TELEMETRY", "durable": False}

    if not configured and verify and verify.get("backend") == "S3":
        ready = (
            verify.get("status") == "READY"
            and bool(verify.get("readback_match"))
            and bool(verify.get("durable"))
        )
        return {
            "configured": True,
            "backend": "S3",
            "status": "OK" if ready else "ATTENTION",
            "storage_verification_status": verify.get("status"),
            "storage_verified_at_utc": verify.get("run_at_utc"),
            "storage_readback_match": bool(verify.get("readback_match")),
            "bucket": verify.get("bucket"),
            "prefix": verify.get("prefix"),
            "manifest_observations": None,
            "unique_payloads": None,
            "unique_paths": None,
            "manifest_invalid_lines": None,
            "manifest_payload_bytes": None,
            "inventory_note": "Remote S3/R2 object counts are intentionally not fetched by this provider-free readiness stage.",
        }

    result = {
        "configured": configured,
        "backend": "LOCAL" if configured else None,
        "status": "STORAGE_NOT_CONFIGURED" if not configured else "CONFIGURED_EMPTY_OR_MISSING",
        "storage_verification_status": None,
        "storage_verified_at_utc": None,
        "storage_readback_match": None,
        "manifest_observations": None if not configured else 0,
        "unique_payloads": None if not configured else 0,
        "unique_paths": None if not configured else 0,
        "manifest_invalid_lines": None if not configured else 0,
        "manifest_payload_bytes": None if not configured else 0,
    }
    if not configured:
        return result
    manifest = archive_dir / "manifest.jsonl"
    if not manifest.exists():
        return result

    observations = 0
    hashes = set()
    paths = set()
    invalid = 0
    payload_bytes = 0
    with manifest.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue
            observations += 1
            if row.get("payload_sha256"):
                hashes.add(str(row["payload_sha256"]))
            if row.get("path"):
                paths.add(str(row["path"]))
            try:
                payload_bytes += int(row.get("payload_bytes") or 0)
            except (TypeError, ValueError):
                invalid += 1
    result.update({
        "status": "OK" if invalid == 0 else "ATTENTION",
        "manifest_observations": observations,
        "unique_payloads": len(hashes),
        "unique_paths": len(paths),
        "manifest_invalid_lines": invalid,
        "manifest_payload_bytes": payload_bytes,
    })
    return result


def build_report(ops=OPS, archive_dir=None):
    data = {name: read_csv(Path(ops) / filename) for name, filename in SOURCES.items()}
    source_presence = {
        name: {
            "file": filename,
            "present": rows is not None,
            "rows": None if rows is None else len(rows),
        }
        for (name, filename), rows in zip(SOURCES.items(), data.values())
    }

    fixtures = data["fixtures"] or []
    finished = [row for row in fixtures if is_finished_fixture(row)]
    finished_ids = {sval(row, "fixture_id") for row in finished if sval(row, "fixture_id")}

    fixture_history = data["fixture_history"] or []
    fixture_history_valid = [
        row for row in fixture_history
        if sval(row, "fixture_id") and sval(row, "observed_at_utc")
    ]
    fixture_history_ids = {sval(row, "fixture_id") for row in fixture_history_valid}
    fixture_history_observation_keys = {
        (sval(row, "fixture_id"), sval(row, "observed_at_utc"))
        for row in fixture_history_valid
    }
    fixture_history_run_times = {sval(row, "observed_at_utc") for row in fixture_history_valid}
    fixture_history_finished_ids = {
        sval(row, "fixture_id") for row in fixture_history_valid if is_finished_fixture(row)
    }
    fixture_history_invalid = len(fixture_history) - len(fixture_history_valid)

    historical_fixtures = data["historical_fixtures"] or []
    historical_fixture_valid = [row for row in historical_fixtures if sval(row, "fixture_id")]
    historical_fixture_ids = {sval(row, "fixture_id") for row in historical_fixture_valid}
    historical_fixture_invalid = len(historical_fixtures) - len(historical_fixture_valid)
    historical_fixture_duplicate_ids = len(historical_fixture_valid) - len(historical_fixture_ids)
    historical_fixture_terminal_ids = {
        sval(row, "fixture_id") for row in historical_fixture_valid
        if is_true(row.get("terminal_observed"))
    }
    historical_fixture_rescheduled_ids = {
        sval(row, "fixture_id") for row in historical_fixture_valid
        if is_true(row.get("reschedule_observed"))
    }
    catalog_missing_history_ids = fixture_history_ids - historical_fixture_ids
    catalog_orphan_ids = historical_fixture_ids - fixture_history_ids
    catalog_missing_terminal_ids = fixture_history_finished_ids - historical_fixture_terminal_ids
    catalog_orphan_terminal_ids = historical_fixture_terminal_ids - fixture_history_finished_ids
    observation_count_total = 0
    observation_count_invalid = 0
    for row in historical_fixture_valid:
        try:
            observation_count_total += int(sval(row, "observation_count") or "0")
        except ValueError:
            observation_count_invalid += 1
    expected_observation_count = len(fixture_history_valid)

    stats = data["player_stats"] or []
    grades = data["player_grades"] or []
    stat_fixture_ids = {sval(row, "fixture_id") for row in stats if sval(row, "fixture_id")}
    grade_fixture_ids = {sval(row, "fixture_id") for row in grades if sval(row, "fixture_id")}
    completed_player_fixture_ids = stat_fixture_ids & grade_fixture_ids

    backlog = data["stage77_backlog"] or []
    backlog_fixture_ids = {sval(row, "fixture_id") for row in backlog if sval(row, "fixture_id")}
    backlog_captured_ids = {
        sval(row, "fixture_id") for row in backlog
        if sval(row, "fixture_id") and sval(row, "backlog_status").upper() == "CAPTURED"
    }
    backlog_pending_ids = backlog_fixture_ids - backlog_captured_ids
    backlog_captured_without_ledgers = backlog_captured_ids - completed_player_fixture_ids
    pending_first_queued = sorted(
        sval(row, "first_queued_at_utc") for row in backlog
        if sval(row, "fixture_id") in backlog_pending_ids and sval(row, "first_queued_at_utc")
    )

    team_stats = data["team_stats"] or []
    team_stat_sides = defaultdict(set)
    for row in team_stats:
        fixture_id = sval(row, "fixture_id")
        team_id = sval(row, "team_id")
        side = sval(row, "side").upper()
        if fixture_id and team_id and side in {"HOME", "AWAY"}:
            team_stat_sides[fixture_id].add(side)

    team_stats_fixture_ids = {
        fixture_id
        for fixture_id, sides in team_stat_sides.items()
        if {"HOME", "AWAY"}.issubset(sides)
    }

    team_xg_rows = 0
    team_xg_sides = defaultdict(set)
    for row in team_stats:
        fixture_id = sval(row, "fixture_id")
        side = sval(row, "side").upper()
        xg = fnum(row.get("expected_goals"))
        if fixture_id and side in {"HOME", "AWAY"} and xg is not None and xg >= 0:
            team_xg_rows += 1
            team_xg_sides[fixture_id].add(side)
    team_xg_complete_fixture_ids = {
        fixture_id
        for fixture_id, sides in team_xg_sides.items()
        if {"HOME", "AWAY"}.issubset(sides)
    }

    stage81_backlog = data["stage81_backlog"] or []
    stage81_backlog_fixture_ids = {
        sval(row, "fixture_id")
        for row in stage81_backlog
        if sval(row, "fixture_id")
    }
    stage81_backlog_captured_ids = {
        sval(row, "fixture_id")
        for row in stage81_backlog
        if sval(row, "fixture_id")
        and sval(row, "backlog_status").upper() == "CAPTURED"
    }
    stage81_backlog_pending_ids = (
        stage81_backlog_fixture_ids - stage81_backlog_captured_ids
    )
    stage81_captured_without_ledger = (
        stage81_backlog_captured_ids - team_stats_fixture_ids
    )
    stage81_pending_first_queued = sorted(
        sval(row, "first_queued_at_utc")
        for row in stage81_backlog
        if sval(row, "fixture_id") in stage81_backlog_pending_ids
        and sval(row, "first_queued_at_utc")
    )

    league_finished = defaultdict(set)
    league_stats = defaultdict(set)
    fixture_to_league = {}
    for row in fixtures:
        fixture_id = sval(row, "fixture_id")
        league = sval(row, "league_name") or sval(row, "provider_league_id") or "UNKNOWN"
        if fixture_id:
            fixture_to_league[fixture_id] = league
        if fixture_id and is_finished_fixture(row):
            league_finished[league].add(fixture_id)
    for fixture_id in stat_fixture_ids:
        league = fixture_to_league.get(fixture_id)
        if league:
            league_stats[league].add(fixture_id)
    per_league = []
    for league in sorted(set(league_finished) | set(league_stats)):
        den = len(league_finished[league])
        num = len(league_stats[league] & league_finished[league]) if den else 0
        per_league.append({
            "league": league,
            "finished_fixtures_in_current_inventory": den,
            "finished_fixtures_with_player_stats": num,
            "player_stats_coverage_pct": pct(num, den),
        })

    current_rosters = data["current_rosters"] or []
    history = data["roster_history"] or []
    intervals = data["membership_intervals"] or []
    transfers = data["transfer_history"] or []
    player_xg_xa = data["player_xg_xa_research"] or []
    contexts = data["match_context"] or []
    lineup_archive = data["lineup_archive"] or []
    injury_archive = data["injury_archive"] or []
    match_events = data["match_events"] or []
    match_event_backlog = data["match_event_backlog"] or []

    history_snapshots = {
        (sval(row, "team_id"), sval(row, "captured_at_utc"))
        for row in history
        if sval(row, "team_id") and sval(row, "captured_at_utc")
    }
    transfer_valid = [
        row for row in transfers
        if sval(row, "transfer_event_id")
        and sval(row, "pbk_player_id")
        and sval(row, "transfermarkt_player_id")
        and sval(row, "transfer_date")
        and sval(row, "mapping_method") == "EXACT_NAME_CURRENT_CLUB"
        and sval(row, "mapping_confidence") == "HIGH"
    ]
    transfer_invalid = len(transfers) - len(transfer_valid)
    transfer_dates = sorted(sval(row, "transfer_date") for row in transfer_valid if sval(row, "transfer_date"))
    transfer_pbk_players = {sval(row, "pbk_player_id") for row in transfer_valid if sval(row, "pbk_player_id")}
    transfer_tm_players = {sval(row, "transfermarkt_player_id") for row in transfer_valid if sval(row, "transfermarkt_player_id")}

    player_xg_xa_valid = [
        row for row in player_xg_xa
        if sval(row, "record_id")
        and sval(row, "statsbomb_match_id")
        and sval(row, "statsbomb_player_id")
        and sval(row, "statsbomb_team_id")
        and sval(row, "source_event_sha256")
        and sval(row, "source") == "StatsBomb Open Data"
        and sval(row, "xg_source_field") == "shot.statsbomb_xg"
        and sval(row, "xa_derivation_method") == "JOIN_PASS_EVENT_ID_TO_SHOT_KEY_PASS_ID_THEN_ASSIGN_SHOT_XG"
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
    ]
    player_xg_xa_invalid = len(player_xg_xa) - len(player_xg_xa_valid)
    player_xg_xa_matches = {
        sval(row, "statsbomb_match_id")
        for row in player_xg_xa_valid
        if sval(row, "statsbomb_match_id")
    }
    player_xg_xa_players = {
        sval(row, "statsbomb_player_id")
        for row in player_xg_xa_valid
        if sval(row, "statsbomb_player_id")
    }
    if data["player_xg_xa_research"] is None:
        player_xg_xa_source_status = "RESEARCH_ADAPTER_READY_NOT_MATERIALIZED"
    elif not player_xg_xa_valid:
        player_xg_xa_source_status = "RESEARCH_SOURCE_EMPTY_OR_INVALID"
    else:
        player_xg_xa_source_status = "RESEARCH_ONLY_MATERIALIZED_NOT_OPERATIONAL"

    context_fixture_ids = {sval(row, "api_fixture_id") for row in contexts if sval(row, "api_fixture_id")}
    lineup_fixture_ids = {
        sval(row, "api_fixture_id") for row in contexts
        if sval(row, "api_fixture_id") and is_true(row.get("lineups_available"))
    }
    injury_fixture_ids = set()
    for row in contexts:
        fixture_id = sval(row, "api_fixture_id")
        if not fixture_id:
            continue
        try:
            injuries_count = int(float(sval(row, "injuries_count") or "0"))
        except ValueError:
            injuries_count = 0
        if injuries_count > 0 or sval(row, "injuries_json") not in {"", "[]", "{}", "null"}:
            injury_fixture_ids.add(fixture_id)

    lineup_archive_fixture_ids = {sval(row, "fixture_id") for row in lineup_archive if sval(row, "fixture_id")}
    injury_archive_fixture_ids = {sval(row, "fixture_id") for row in injury_archive if sval(row, "fixture_id")}
    match_event_fixture_ids = {sval(row, "fixture_id") for row in match_events if sval(row, "fixture_id")}
    event_backlog_ids = {sval(row, "fixture_id") for row in match_event_backlog if sval(row, "fixture_id")}
    event_backlog_pending = {sval(row, "fixture_id") for row in match_event_backlog if sval(row, "fixture_id") and sval(row, "backlog_status").upper() == "PENDING"}
    event_backlog_captured = {sval(row, "fixture_id") for row in match_event_backlog if sval(row, "fixture_id") and sval(row, "backlog_status").upper() == "CAPTURED"}
    raw_archive = raw_archive_inventory(archive_dir, ops=ops)
    roster_history_rows = len(history)
    player_stats_fixture_count = len(stat_fixture_ids)

    gaps = []
    if data["fixture_history"] is None or len(fixture_history_valid) == 0:
        gaps.append("FIXTURE_HISTORY_WAITING_FIRST_PRODUCTION_SEED")
    if fixture_history_invalid:
        gaps.append("FIXTURE_HISTORY_INVALID_IDENTITY_ROWS")
    if data["historical_fixtures"] is None:
        gaps.append("HISTORICAL_FIXTURE_CATALOG_WAITING_FIRST_BUILD")
    if historical_fixture_invalid:
        gaps.append("HISTORICAL_FIXTURE_CATALOG_INVALID_IDENTITY_ROWS")
    if historical_fixture_duplicate_ids:
        gaps.append("HISTORICAL_FIXTURE_CATALOG_DUPLICATE_FIXTURE_IDS")
    if fixture_history_ids and data["historical_fixtures"] is not None and catalog_missing_history_ids:
        gaps.append("HISTORICAL_FIXTURE_CATALOG_MISSING_HISTORY_FIXTURES")
    if data["fixture_history"] is not None and historical_fixture_ids and catalog_orphan_ids:
        gaps.append("HISTORICAL_FIXTURE_CATALOG_ORPHAN_FIXTURES")
    if fixture_history_ids and historical_fixture_ids and (catalog_missing_terminal_ids or catalog_orphan_terminal_ids):
        gaps.append("HISTORICAL_FIXTURE_CATALOG_TERMINAL_EVIDENCE_MISMATCH")
    if fixture_history_ids and historical_fixture_ids and (observation_count_invalid or observation_count_total != expected_observation_count):
        gaps.append("HISTORICAL_FIXTURE_CATALOG_OBSERVATION_COUNT_MISMATCH")
    if data["roster_history"] is None or roster_history_rows == 0:
        gaps.append("ROSTER_HISTORY_WAITING_FIRST_CAPTURE")
    if data["membership_intervals"] is None or len(intervals) == 0:
        gaps.append("MEMBERSHIP_INTERVALS_WAITING_HISTORY")
    if data["team_stats"] is None or len(team_stats_fixture_ids) == 0:
        gaps.append("TEAM_STATS_NO_CAPTURED_FIXTURES")
    if data["stage81_backlog"] is None:
        gaps.append("STAGE81_BACKLOG_WAITING_FIRST_OPERATIONAL_RUN")
    elif stage81_backlog_pending_ids:
        gaps.append("TEAM_STATS_BACKLOG_PENDING")
    if stage81_captured_without_ledger:
        gaps.append("STAGE81_BACKLOG_CAPTURED_LEDGER_MISMATCH")
    if data["player_stats"] is None or player_stats_fixture_count == 0:
        gaps.append("PLAYER_STATS_NO_CAPTURED_FIXTURES")
    if data["stage77_backlog"] is None:
        gaps.append("STAGE77_BACKLOG_WAITING_FIRST_OPERATIONAL_RUN")
    elif backlog_pending_ids:
        gaps.append("PLAYER_STATS_BACKLOG_PENDING")
    if backlog_captured_without_ledgers:
        gaps.append("STAGE77_BACKLOG_CAPTURED_LEDGER_MISMATCH")
    if len(finished_ids) == 0:
        gaps.append("CURRENT_INVENTORY_HAS_NO_FINISHED_FIXTURE_DENOMINATOR")
    elif len(stat_fixture_ids & finished_ids) < len(finished_ids):
        gaps.append("PLAYER_STATS_PARTIAL_FINISHED_FIXTURE_COVERAGE")
    if finished_ids and len(team_stats_fixture_ids & finished_ids) < len(finished_ids):
        gaps.append("TEAM_STATS_PARTIAL_FINISHED_FIXTURE_COVERAGE")
    if data["match_events"] is None:
        gaps.append("MATCH_EVENT_ARCHIVE_WAITING_FIRST_CAPTURE")
    if data["match_event_backlog"] is None:
        gaps.append("MATCH_EVENT_BACKLOG_WAITING_FIRST_OPERATIONAL_RUN")
    elif event_backlog_pending:
        gaps.append("MATCH_EVENT_BACKLOG_PENDING")
    if data["lineup_archive"] is None:
        gaps.append("LINEUP_ARCHIVE_WAITING_FIRST_BUILD")
    if data["injury_archive"] is None:
        gaps.append("INJURY_ARCHIVE_WAITING_FIRST_BUILD")
    if not raw_archive["configured"]:
        gaps.append("RAW_ARCHIVE_DURABLE_STORAGE_NOT_CONFIGURED")
    elif raw_archive["status"] != "OK":
        gaps.append("RAW_ARCHIVE_STORAGE_NEEDS_ATTENTION")
    gaps.append("MATCH_CONTEXT_COVERAGE_IS_CANONICAL_SCOPE_ONLY")
    if data["transfer_history"] is None or not transfer_valid:
        gaps.append("VERIFIED_TRANSFER_EVENTS_NOT_YET_INGESTED")
    if transfer_invalid:
        gaps.append("TRANSFER_HISTORY_INVALID_IDENTITY_ROWS")
    if data["team_stats"] is None or team_xg_rows == 0:
        gaps.append("TEAM_XG_NO_VERIFIED_OBSERVATIONS")
    elif (
        not team_xg_complete_fixture_ids
        or len(team_xg_complete_fixture_ids) < len(team_stats_fixture_ids)
    ):
        gaps.append("TEAM_XG_PARTIAL_CAPTURED_FIXTURE_COVERAGE")
    if data["player_xg_xa_research"] is None:
        gaps.append("PLAYER_XG_XA_RESEARCH_SOURCE_NOT_MATERIALIZED")
    elif not player_xg_xa_valid:
        gaps.append("PLAYER_XG_XA_RESEARCH_SOURCE_INVALID")
    else:
        gaps.append("PLAYER_XG_XA_PBK_IDENTITY_MAPPING_NOT_IMPLEMENTED")
    if player_xg_xa_invalid:
        gaps.append("PLAYER_XG_XA_RESEARCH_SOURCE_INVALID_ROWS")

    if roster_history_rows == 0 and player_stats_fixture_count == 0:
        status = "BOOTSTRAPPING"
    else:
        status = "COLLECTING"

    report = {
        "version": VERSION,
        "generated_at_utc": iso_now(),
        "status": status,
        "scope": "historical archive telemetry only",
        "source_presence": source_presence,
        "fixtures": {
            "current_inventory": len(fixtures),
            "finished_in_current_inventory": len(finished_ids),
            "player_stats_fixture_count_all_snapshots": len(stat_fixture_ids),
            "player_grade_fixture_count_all_snapshots": len(grade_fixture_ids),
            "finished_current_inventory_with_player_stats": len(finished_ids & stat_fixture_ids),
            "finished_current_inventory_player_stats_coverage_pct": pct(len(finished_ids & stat_fixture_ids), len(finished_ids)),
            "per_league": per_league,
        },
        "fixture_history": {
            "present": data["fixture_history"] is not None,
            "rows": len(fixture_history),
            "valid_observations": len(fixture_history_observation_keys),
            "unique_fixtures": len(fixture_history_ids),
            "observation_runs": len(fixture_history_run_times),
            "finished_fixtures_observed": len(fixture_history_finished_ids),
            "invalid_identity_rows": fixture_history_invalid,
            "evidence_note": "Counts represent only Stage71 current-round observations persisted after the fixture-history archive was enabled; they are not a pre-PBK historical backfill claim.",
        },
        "historical_fixture_catalog": {
            "present": data["historical_fixtures"] is not None,
            "rows": len(historical_fixtures),
            "valid_rows": len(historical_fixture_valid),
            "unique_fixtures": len(historical_fixture_ids),
            "terminal_fixtures": len(historical_fixture_terminal_ids),
            "rescheduled_fixtures": len(historical_fixture_rescheduled_ids),
            "invalid_identity_rows": historical_fixture_invalid,
            "duplicate_fixture_ids": historical_fixture_duplicate_ids,
            "history_fixture_coverage_pct": pct(len(fixture_history_ids & historical_fixture_ids), len(fixture_history_ids)),
            "missing_history_fixtures": len(catalog_missing_history_ids),
            "orphan_catalog_fixtures": len(catalog_orphan_ids),
            "missing_terminal_evidence": len(catalog_missing_terminal_ids),
            "orphan_terminal_evidence": len(catalog_orphan_terminal_ids),
            "observation_count_total": observation_count_total,
            "expected_history_observations": expected_observation_count,
            "invalid_observation_count_rows": observation_count_invalid,
            "evidence_note": "historical_fixtures is a deterministic warehouse projection only; fixture_history_snapshots remains the append-only historical evidence source-of-truth.",
        },
        "stage77_backlog": {
            "present": data["stage77_backlog"] is not None,
            "total_fixtures": len(backlog_fixture_ids),
            "pending_fixtures": len(backlog_pending_ids),
            "captured_fixtures": len(backlog_captured_ids),
            "captured_without_complete_ledgers": len(backlog_captured_without_ledgers),
            "oldest_pending_first_queued_at_utc": pending_first_queued[0] if pending_first_queued else None,
            "evidence_note": "A pending backlog fixture is an observed terminal fixture awaiting player stats/Player Grade; it is not a provider-availability or completeness claim.",
        },
        "stage81_backlog": {
            "present": data["stage81_backlog"] is not None,
            "total_fixtures": len(stage81_backlog_fixture_ids),
            "pending_fixtures": len(stage81_backlog_pending_ids),
            "captured_fixtures": len(stage81_backlog_captured_ids),
            "captured_without_complete_ledger": len(stage81_captured_without_ledger),
            "oldest_pending_first_queued_at_utc": stage81_pending_first_queued[0] if stage81_pending_first_queued else None,
            "evidence_note": "Pending means PBK observed a terminal fixture but has not yet persisted complete HOME+AWAY /fixtures/statistics evidence.",
        },
        "team_statistics": {
            "rows": len(team_stats),
            "complete_fixture_count": len(team_stats_fixture_ids),
            "finished_current_inventory_with_team_stats": len(
                finished_ids & team_stats_fixture_ids
            ),
            "finished_current_inventory_team_stats_coverage_pct": pct(
                len(finished_ids & team_stats_fixture_ids),
                len(finished_ids),
            ),
            "evidence_note": "Complete means HOME and AWAY team rows exist; individual missing provider metrics remain UNKNOWN.",
        },
        "advanced_metrics": {
            "team_xg_source": "API-Football /fixtures/statistics expected_goals",
            "team_xg_rows": team_xg_rows,
            "team_xg_complete_fixture_count": len(team_xg_complete_fixture_ids),
            "team_stats_complete_fixture_count": len(team_stats_fixture_ids),
            "team_xg_captured_fixture_coverage_pct": pct(
                len(team_xg_complete_fixture_ids & team_stats_fixture_ids),
                len(team_stats_fixture_ids),
            ),
            "finished_current_inventory_with_team_xg": len(
                finished_ids & team_xg_complete_fixture_ids
            ),
            "finished_current_inventory_team_xg_coverage_pct": pct(
                len(finished_ids & team_xg_complete_fixture_ids),
                len(finished_ids),
            ),
            "team_xg_evidence_note": "Verified provider field when present; API-Football may return it as missing for some competitions or fixtures and PBK preserves missing as UNKNOWN.",
            "player_xg_xa_source_status": player_xg_xa_source_status,
            "player_xg_xa_research_rows": len(player_xg_xa_valid),
            "player_xg_xa_research_invalid_rows": player_xg_xa_invalid,
            "player_xg_xa_research_matches": len(player_xg_xa_matches),
            "player_xg_xa_research_unique_players": len(player_xg_xa_players),
            "player_xg_source": "StatsBomb Open Data shot.statsbomb_xg when Stage91 is materialized",
            "player_xa_method": "Derived by joining pass event id to shot.key_pass_id and assigning the created shot xG",
            "player_xg_xa_attribution_required": True,
            "player_xg_xa_operational_authority": False,
            "player_xg_xa_pbk_identity_mapping": "NOT_IMPLEMENTED",
            "player_xg_xa_evidence_note": "Stage91 is a research-only StatsBomb identity projection. Raw StatsBomb events are not committed to PBK. Materialized rows do not become API-Football/PBK player authority until a separate conservative identity mapping is implemented.",
        },
        "players": {
            "player_stat_rows": len(stats),
            "unique_players_with_stats": uniq(stats, "player_id") or 0,
            "player_grade_rows": len(grades),
            "unique_players_with_grades": uniq(grades, "player_id") or 0,
        },
        "rosters": {
            "current_roster_rows": len(current_rosters),
            "current_roster_teams": uniq(current_rosters, "team_id") or 0,
            "history_rows": roster_history_rows,
            "history_teams": uniq(history, "team_id") or 0,
            "history_team_snapshots": len(history_snapshots),
            "membership_intervals": len(intervals),
            "open_latest_intervals": sum(1 for row in intervals if sval(row, "interval_status") == "OPEN_LATEST"),
            "closed_by_observed_absence_intervals": sum(1 for row in intervals if sval(row, "interval_status") == "CLOSED_BY_OBSERVED_ABSENCE"),
        },
        "transfer_history": {
            "present": data["transfer_history"] is not None,
            "rows": len(transfers),
            "valid_rows": len(transfer_valid),
            "invalid_identity_rows": transfer_invalid,
            "unique_pbk_players": len(transfer_pbk_players),
            "unique_transfermarkt_players": len(transfer_tm_players),
            "earliest_transfer_date": transfer_dates[0] if transfer_dates else None,
            "latest_transfer_date": transfer_dates[-1] if transfer_dates else None,
            "evidence_note": "Only durable HIGH-confidence EXACT_NAME_CURRENT_CLUB mapped Transfermarkt events count as verified historical transfer enrichment; this is not current squad authority.",
        },
        "context": {
            "snapshot_rows": len(contexts),
            "unique_fixtures": len(context_fixture_ids),
            "fixtures_with_official_lineup_snapshot": len(lineup_fixture_ids),
            "fixtures_with_injury_evidence": len(injury_fixture_ids),
            "coverage_note": "Stage55 context is canonical-signal scoped; these counts are not full 16-league archive coverage.",
        },
        "match_events": {
            "event_rows": len(match_events),
            "event_fixtures": len(match_event_fixture_ids),
            "backlog_total_fixtures": len(event_backlog_ids),
            "backlog_pending_fixtures": len(event_backlog_pending),
            "backlog_captured_fixtures": len(event_backlog_captured),
            "evidence_note": "Append-only normalized provider match events captured only after PBK observed a terminal fixture; empty provider responses remain retryable.",
        },
        "normalized_context_archives": {
            "lineup_rows": len(lineup_archive),
            "lineup_fixtures": len(lineup_archive_fixture_ids),
            "injury_rows": len(injury_archive),
            "injury_fixtures": len(injury_archive_fixture_ids),
            "evidence_note": "Provider-free normalized append-only projections from already-persisted PBK context/rotation evidence; coverage remains limited by upstream capture scope.",
        },
        "raw_provider_archive": raw_archive,
        "gaps": gaps,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "provider_calls": 0,
    }
    return report


def render_markdown(report):
    f = report["fixtures"]
    fh = report["fixture_history"]
    fc = report["historical_fixture_catalog"]
    b = report["stage77_backlog"]
    b81 = report["stage81_backlog"]
    ts = report["team_statistics"]
    r = report["rosters"]
    p = report["players"]
    advanced = report["advanced_metrics"]
    c = report["context"]
    transfers = report["transfer_history"]
    events = report["match_events"]
    norm = report["normalized_context_archives"]
    raw = report["raw_provider_archive"]
    coverage = f["finished_current_inventory_player_stats_coverage_pct"]
    coverage_text = "—" if coverage is None else f"{coverage:.2f}%"
    team_stats_coverage = ts["finished_current_inventory_team_stats_coverage_pct"]
    team_stats_coverage_text = "—" if team_stats_coverage is None else f"{team_stats_coverage:.2f}%"
    team_xg_coverage = advanced["team_xg_captured_fixture_coverage_pct"]
    team_xg_coverage_text = "—" if team_xg_coverage is None else f"{team_xg_coverage:.2f}%"
    catalog_coverage = fc["history_fixture_coverage_pct"]
    catalog_coverage_text = "—" if catalog_coverage is None else f"{catalog_coverage:.2f}%"
    lines = [
        "# PBK Stage80 Archive Readiness",
        "",
        f"Обновлено UTC: {report['generated_at_utc']}",
        f"Статус: **{report['status']}**",
        "",
        "## Покрытие",
        f"- Fixtures в текущем inventory: {f['current_inventory']} (finished: {f['finished_in_current_inventory']}).",
        f"- Fixture history: {fh['unique_fixtures']} unique fixtures / {fh['valid_observations']} observations / {fh['observation_runs']} observation runs (finished observed: {fh['finished_fixtures_observed']}).",
        f"- Historical fixture catalog: {fc['unique_fixtures']} fixtures (terminal {fc['terminal_fixtures']}, rescheduled {fc['rescheduled_fixtures']}), history coverage {catalog_coverage_text}; missing {fc['missing_history_fixtures']}, orphan {fc['orphan_catalog_fixtures']}.",
        f"- Finished fixtures с player stats: {f['finished_current_inventory_with_player_stats']} / {f['finished_in_current_inventory']} ({coverage_text}).",
        f"- Stage77 durable backlog: pending {b['pending_fixtures']}; captured {b['captured_fixtures']}; total {b['total_fixtures']}.",
        f"- Normalized lineup archive: {norm['lineup_rows']} rows / {norm['lineup_fixtures']} fixtures; injury archive: {norm['injury_rows']} rows / {norm['injury_fixtures']} fixtures.",
        f"- Match event archive: {events['event_rows']} rows / {events['event_fixtures']} fixtures; backlog pending {events['backlog_pending_fixtures']} / total {events['backlog_total_fixtures']}.",
        f"- Stage81 durable backlog: pending {b81['pending_fixtures']}; captured {b81['captured_fixtures']}; total {b81['total_fixtures']}.",
        f"- Team match statistics: {ts['complete_fixture_count']} complete fixtures / {ts['rows']} team rows; current finished coverage {team_stats_coverage_text}.",
        f"- Team xG: {advanced['team_xg_complete_fixture_count']} complete fixtures / {advanced['team_xg_rows']} team rows; captured-team-stat coverage {team_xg_coverage_text}.",
        f"- Player xG/xA source: {advanced['player_xg_xa_source_status']}.",
        f"- Player stat rows: {p['player_stat_rows']}; уникальных игроков: {p['unique_players_with_stats']}.",
        f"- Player Grade rows: {p['player_grade_rows']}; уникальных игроков: {p['unique_players_with_grades']}.",
        f"- Current roster: {r['current_roster_teams']} команд / {r['current_roster_rows']} игроковых строк.",
        f"- Roster history: {r['history_teams']} команд / {r['history_team_snapshots']} team-snapshots / {r['history_rows']} строк.",
        f"- Membership intervals: {r['membership_intervals']} (open {r['open_latest_intervals']}, closed-by-observed-absence {r['closed_by_observed_absence_intervals']}).",
        f"- Verified historical transfers: {transfers['valid_rows']} rows / {transfers['unique_pbk_players']} PBK players; dates {transfers['earliest_transfer_date'] or '—'} → {transfers['latest_transfer_date'] or '—'}; invalid {transfers['invalid_identity_rows']}.",
        f"- Match context: {c['unique_fixtures']} fixtures; official XI {c['fixtures_with_official_lineup_snapshot']}; injury evidence {c['fixtures_with_injury_evidence']}.",
        "",
        "## Raw provider archive",
        f"- Storage configured: {raw['configured']}.",
        f"- Backend: {raw.get('backend') or '—'}.",
        f"- Status: {raw['status']}.",
        f"- Durable readback verified: {raw.get('storage_readback_match') if raw.get('storage_readback_match') is not None else '—'}; verified at {raw.get('storage_verified_at_utc') or '—'}.",
        f"- Observations: {raw['manifest_observations'] if raw['manifest_observations'] is not None else '—'}; unique payloads: {raw['unique_payloads'] if raw['unique_payloads'] is not None else '—'}.",
        "",
        "## Незакрытые пробелы",
    ]
    lines.extend(f"- {gap}" for gap in report["gaps"])
    lines += [
        "",
        "Readiness — telemetry only. Этот отчёт не создаёт ставки, не меняет probability/EV, eligibility, stake или Forward journal.",
    ]
    return "\n".join(lines) + "\n"


def main():
    report = build_report()
    OPS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "provider_calls": 0,
        "gaps": len(report["gaps"]),
        "fixture_history_observations": report["fixture_history"]["valid_observations"],
        "historical_fixture_catalog_rows": report["historical_fixture_catalog"]["unique_fixtures"],
        "historical_fixture_catalog_coverage_pct": report["historical_fixture_catalog"]["history_fixture_coverage_pct"],
        "stage77_backlog_pending": report["stage77_backlog"]["pending_fixtures"],
        "stage81_backlog_pending": report["stage81_backlog"]["pending_fixtures"],
        "team_stats_complete_fixtures": report["team_statistics"]["complete_fixture_count"],
        "roster_history_rows": report["rosters"]["history_rows"],
        "player_stats_fixtures": report["fixtures"]["player_stats_fixture_count_all_snapshots"],
        "raw_archive_status": report["raw_provider_archive"]["status"],
        "verified_transfer_rows": report["transfer_history"]["valid_rows"],
        "team_xg_complete_fixtures": report["advanced_metrics"]["team_xg_complete_fixture_count"],
        "player_xg_xa_source_status": report["advanced_metrics"]["player_xg_xa_source_status"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
