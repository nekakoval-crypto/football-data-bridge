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
VERSION = "PBK_STAGE80_ARCHIVE_READINESS_V28_INTERNATIONAL_WINDOW_REFERENCE_V2"

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
    "player_profiles": "player_profile_evidence.csv",
    "roster_history": "team_roster_history.csv",
    "membership_intervals": "team_membership_intervals.csv",
    "transfer_identity": "pbk_transfermarkt_player_identity.csv",
    "transfer_history": "historical_transfer_events.csv",
    "match_context": "match_context_snapshots.csv",
    "lineup_archive": "lineup_snapshots.csv",
    "injury_archive": "injury_snapshots.csv",
    "match_events": "match_event_snapshots.csv",
    "match_event_backlog": "stage80_match_event_backlog.csv",
    "player_xg_xa_research": "statsbomb_player_xg_xa.csv",
    "player_xg_xa_mapping": "statsbomb_pbk_player_mapping_candidates.csv",
    "player_xg_xa_mapped": "pbk_player_xg_xa_research.csv",
    "referee_profiles": "epl_referee_profiles_research.csv",
    "referee_team_splits": "epl_referee_team_splits_research.csv",
    "top5_referee_fixtures": "top5_referee_fixture_history.csv",
    "top5_referee_profiles": "top5_referee_profiles_research.csv",
    "top5_referee_team_splits": "top5_referee_team_splits_research.csv",
    "top5_referee_state": "stage80_top5_referee_backfill_state.csv",
    "prematch_context": "top5_prematch_context_research.csv",
    "prematch_factor_research": "top5_prematch_factor_research.csv",
    "prematch_factor_stability": "top5_prematch_factor_stability_research.csv",
    "prematch_walkforward": "top5_prematch_factor_walkforward_research.csv",
    "prematch_walkforward_summary": "top5_prematch_factor_walkforward_summary_research.csv",
    "pbk16_competition_catalog": "stage80_pbk16_competition_catalog.csv",
    "pbk16_competition_fixtures": "pbk16_all_competition_fixture_history.csv",
    "pbk16_competition_state": "stage80_pbk16_competition_backfill_state.csv",
    "pbk16_competition_congestion": "pbk16_competition_congestion_research.csv",
    "pbk16_international_window_context": "pbk16_international_window_context_research.csv",
    "pbk14_market_bridge": "pbk14_football_data_fixture_bridge.csv",
    "pbk14_international_window_market_join": "pbk14_international_window_market_join_research.csv",
    "pbk14_congestion_market_join": "pbk14_congestion_market_join_research.csv",
    "pbk14_congestion_market_profiles": "pbk14_congestion_market_factor_research.csv",
    "pbk14_congestion_market_stability": "pbk14_congestion_market_factor_stability_research.csv",
    "pbk14_congestion_market_walkforward": "pbk14_congestion_market_walkforward_research.csv",
    "pbk14_congestion_market_walkforward_summary": "pbk14_congestion_market_walkforward_summary_research.csv",
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


def read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {"_invalid_json": True}


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
    stage91_meta = read_json(Path(ops) / "stage91_statsbomb_player_xg_xa_last_run.json")
    referee_meta = read_json(Path(ops) / "stage80_referee_research_last_run.json")
    top5_referee_meta = read_json(Path(ops) / "stage80_top5_referee_backfill_last_run.json")
    prematch_context_meta = read_json(Path(ops) / "stage80_prematch_context_last_run.json")
    prematch_factor_meta = read_json(Path(ops) / "stage80_prematch_factor_research_last_run.json")
    prematch_walkforward_meta = read_json(Path(ops) / "stage80_prematch_factor_walkforward_last_run.json")
    pbk16_competition_meta = read_json(Path(ops) / "stage80_pbk16_competition_backfill_last_run.json")
    pbk16_congestion_meta = read_json(Path(ops) / "stage80_pbk16_competition_congestion_last_run.json")
    pbk16_international_meta = read_json(Path(ops) / "stage80_pbk16_international_window_context_last_run.json")
    pbk14_market_source_meta = read_json(Path(ops) / "stage80_football_data_pbk14_history_last_run.json")
    pbk14_market_bridge_meta = read_json(Path(ops) / "stage80_pbk14_fixture_bridge_last_run.json")
    pbk14_international_join_meta = read_json(Path(ops) / "stage80_pbk14_international_window_market_join_last_run.json")
    pbk14_congestion_join_meta = read_json(Path(ops) / "stage80_pbk14_congestion_market_join_last_run.json")
    pbk14_congestion_research_meta = read_json(Path(ops) / "stage80_pbk14_congestion_market_research_last_run.json")
    pbk14_congestion_walkforward_meta = read_json(Path(ops) / "stage80_pbk14_congestion_market_walkforward_last_run.json")
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
    player_profiles = data["player_profiles"] or []
    history = data["roster_history"] or []
    intervals = data["membership_intervals"] or []
    transfer_identity = data["transfer_identity"] or []
    transfers = data["transfer_history"] or []
    player_xg_xa = data["player_xg_xa_research"] or []
    player_xg_xa_mapping = data["player_xg_xa_mapping"] or []
    player_xg_xa_mapped = data["player_xg_xa_mapped"] or []
    contexts = data["match_context"] or []
    lineup_archive = data["lineup_archive"] or []
    injury_archive = data["injury_archive"] or []
    match_events = data["match_events"] or []
    match_event_backlog = data["match_event_backlog"] or []
    referee_profiles = data["referee_profiles"] or []
    referee_team_splits = data["referee_team_splits"] or []
    top5_referee_fixtures = data["top5_referee_fixtures"] or []
    top5_referee_profiles = data["top5_referee_profiles"] or []
    top5_referee_team_splits = data["top5_referee_team_splits"] or []
    top5_referee_state = data["top5_referee_state"] or []
    prematch_context = data["prematch_context"] or []
    prematch_factor_research = data["prematch_factor_research"] or []
    prematch_factor_stability = data["prematch_factor_stability"] or []
    prematch_walkforward = data["prematch_walkforward"] or []
    prematch_walkforward_summary = data["prematch_walkforward_summary"] or []

    history_snapshots = {
        (sval(row, "team_id"), sval(row, "captured_at_utc"))
        for row in history
        if sval(row, "team_id") and sval(row, "captured_at_utc")
    }
    current_roster_player_ids = {
        sval(row, "player_id")
        for row in current_rosters
        if sval(row, "player_id")
    }
    player_profile_sources = {
        "api-football:/players?team&season",
        "api-football:/players?id&season+current_roster",
    }
    player_profile_valid = [
        row for row in player_profiles
        if sval(row, "team_id")
        and sval(row, "season")
        and sval(row, "player_id")
        and sval(row, "captured_at_utc")
        and sval(row, "source") in player_profile_sources
    ]
    player_profile_team_source_rows = sum(
        1 for row in player_profile_valid
        if sval(row, "source") == "api-football:/players?team&season"
    )
    player_profile_residual_source_rows = sum(
        1 for row in player_profile_valid
        if sval(row, "source") == "api-football:/players?id&season+current_roster"
    )
    player_profile_invalid = len(player_profiles) - len(player_profile_valid)
    player_profile_identity_ready = [
        row for row in player_profile_valid
        if sval(row, "birth_date")
        and (sval(row, "firstname") or sval(row, "player_name"))
        and (sval(row, "lastname") or sval(row, "player_name"))
    ]
    player_profile_ids = {
        sval(row, "player_id")
        for row in player_profile_valid
        if sval(row, "player_id")
    }
    player_profile_identity_ready_ids = {
        sval(row, "player_id")
        for row in player_profile_identity_ready
        if sval(row, "player_id")
    }
    player_profile_team_ids = {
        sval(row, "team_id")
        for row in player_profile_valid
        if sval(row, "team_id")
    }

    transfer_identity_valid = [
        row for row in transfer_identity
        if sval(row, "pbk_player_id")
        and sval(row, "transfermarkt_player_id")
        and sval(row, "mapping_method") in {"EXACT_NAME_CURRENT_CLUB", "EXACT_PROFILE_NAME_DOB_CURRENT_CLUB", "EXACT_STATS_NAME_CURRENT_CLUB"}
        and sval(row, "mapping_confidence") == "HIGH"
        and sval(row, "match_status") == "AUTO_MATCH"
    ]
    transfer_identity_invalid = len(transfer_identity) - len(transfer_identity_valid)
    transfer_identity_pbk_players = {
        sval(row, "pbk_player_id")
        for row in transfer_identity_valid
        if sval(row, "pbk_player_id")
    }
    transfer_identity_tm_players = {
        sval(row, "transfermarkt_player_id")
        for row in transfer_identity_valid
        if sval(row, "transfermarkt_player_id")
    }

    transfer_valid = [
        row for row in transfers
        if sval(row, "transfer_event_id")
        and sval(row, "pbk_player_id")
        and sval(row, "transfermarkt_player_id")
        and sval(row, "transfer_date")
        and sval(row, "mapping_method") in {"EXACT_NAME_CURRENT_CLUB", "EXACT_PROFILE_NAME_DOB_CURRENT_CLUB", "EXACT_STATS_NAME_CURRENT_CLUB"}
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
        and sval(row, "operational_betting_authority").lower() in {"false", "0", "no", "n"}
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
    player_xg_xa_auto_mapping = [
        row for row in player_xg_xa_mapping
        if sval(row, "statsbomb_player_id")
        and sval(row, "pbk_player_id")
        and sval(row, "match_status") == "AUTO_MATCH"
        and sval(row, "match_method") == "EXACT_FULL_NAME_VIA_VERIFIED_TRANSFER"
        and sval(row, "match_confidence") == "HIGH"
        and is_true(row.get("authoritative_for_player_xg_xa"))
    ]
    player_xg_xa_review_mapping = [
        row for row in player_xg_xa_mapping
        if sval(row, "match_status") == "REVIEW"
    ]
    player_xg_xa_mapped_valid = [
        row for row in player_xg_xa_mapped
        if sval(row, "pbk_player_id")
        and sval(row, "statsbomb_player_id")
        and sval(row, "statsbomb_match_id")
        and sval(row, "statsbomb_record_id")
        and sval(row, "source_event_sha256")
        and sval(row, "mapping_method") == "EXACT_FULL_NAME_VIA_VERIFIED_TRANSFER"
        and sval(row, "mapping_confidence") == "HIGH"
        and is_true(row.get("research_only"))
        and sval(row, "operational_betting_authority").lower() in {"false", "0", "no", "n"}
    ]
    player_xg_xa_mapped_invalid = len(player_xg_xa_mapped) - len(player_xg_xa_mapped_valid)
    player_xg_xa_mapped_players = {
        sval(row, "pbk_player_id")
        for row in player_xg_xa_mapped_valid
        if sval(row, "pbk_player_id")
    }
    player_xg_xa_mapped_matches = {
        sval(row, "statsbomb_match_id")
        for row in player_xg_xa_mapped_valid
        if sval(row, "statsbomb_match_id")
    }

    stage91_meta_valid = bool(
        stage91_meta
        and not stage91_meta.get("_invalid_json")
        and stage91_meta.get("version") == "PBK_STAGE91_STATSBOMB_PLAYER_XG_XA_V1"
        and stage91_meta.get("status") == "OK"
        and stage91_meta.get("source") == "StatsBomb Open Data"
        and bool(str(stage91_meta.get("source_revision") or "").strip())
        and int(stage91_meta.get("player_match_rows") or 0) > 0
        and int(stage91_meta.get("unique_statsbomb_players") or 0) > 0
        and stage91_meta.get("raw_data_committed_to_pbk") is False
        and stage91_meta.get("research_only") is True
        and stage91_meta.get("operational_betting_authority") is False
        and int(stage91_meta.get("provider_calls") or 0) == 0
    )
    stage91_external_payload_attested = bool(
        data["player_xg_xa_research"] is None
        and stage91_meta_valid
        and player_xg_xa_auto_mapping
        and player_xg_xa_mapped_valid
    )

    if stage91_external_payload_attested:
        player_xg_xa_source_status = "RESEARCH_SOURCE_EXTERNAL_LOCAL_ATTESTED_MAPPED_TO_PBK"
        player_xg_xa_mapping_status = "AUTO_HIGH_MATERIALIZED"
    elif data["player_xg_xa_research"] is None:
        player_xg_xa_source_status = "RESEARCH_ADAPTER_READY_NOT_MATERIALIZED"
        player_xg_xa_mapping_status = "WAITING_FOR_STAGE91_SOURCE"
    elif not player_xg_xa_valid:
        player_xg_xa_source_status = "RESEARCH_SOURCE_EMPTY_OR_INVALID"
        player_xg_xa_mapping_status = "BLOCKED_INVALID_STAGE91_SOURCE"
    elif data["player_xg_xa_mapping"] is None or data["player_xg_xa_mapped"] is None:
        player_xg_xa_source_status = "RESEARCH_SOURCE_MATERIALIZED_MAPPING_NOT_MATERIALIZED"
        player_xg_xa_mapping_status = "STAGE92_NOT_MATERIALIZED"
    elif not player_xg_xa_auto_mapping or not player_xg_xa_mapped_valid:
        player_xg_xa_source_status = "RESEARCH_SOURCE_MATERIALIZED_NO_HIGH_CONFIDENCE_MAPPING"
        player_xg_xa_mapping_status = "NO_AUTO_HIGH_MAPPING"
    else:
        player_xg_xa_source_status = "RESEARCH_MAPPED_TO_PBK_RESEARCH_ONLY"
        player_xg_xa_mapping_status = "AUTO_HIGH_MATERIALIZED"

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
    referee_profile_valid = [
        row for row in referee_profiles
        if sval(row, "referee")
        and sval(row, "source_scope") == "EPL_ONLY"
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
    ]
    referee_team_split_valid = [
        row for row in referee_team_splits
        if sval(row, "referee")
        and sval(row, "team")
        and sval(row, "source_scope") == "EPL_ONLY"
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
    ]
    referee_profile_invalid = len(referee_profiles) - len(referee_profile_valid)
    referee_team_split_invalid = len(referee_team_splits) - len(referee_team_split_valid)
    referee_meta_valid = bool(
        referee_meta
        and referee_meta.get("status") == "OK"
        and referee_meta.get("source_scope") == "EPL_ONLY"
        and int(referee_meta.get("source_rows") or 0) == 3420
        and int(referee_meta.get("unique_referees") or 0) == len(referee_profile_valid)
        and int(referee_meta.get("referee_team_pairs") or 0) == len(referee_team_split_valid)
        and referee_meta.get("research_only") is True
        and referee_meta.get("operational_betting_authority") is False
        and int(referee_meta.get("provider_calls") or 0) == 0
    )
    top5_referee_fixture_valid = [
        row for row in top5_referee_fixtures
        if sval(row, "fixture_id")
        and sval(row, "provider_league_id")
        and sval(row, "season")
        and sval(row, "home_team_id")
        and sval(row, "away_team_id")
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
    ]
    top5_referee_profile_valid = [
        row for row in top5_referee_profiles
        if sval(row, "provider_league_id")
        and sval(row, "referee")
        and sval(row, "source_scope") == "TOP5_9_SEASONS_API_FOOTBALL"
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
    ]
    top5_referee_team_split_valid = [
        row for row in top5_referee_team_splits
        if sval(row, "provider_league_id")
        and sval(row, "referee")
        and sval(row, "team_id")
        and sval(row, "source_scope") == "TOP5_9_SEASONS_API_FOOTBALL"
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
    ]
    top5_referee_fixture_invalid = len(top5_referee_fixtures) - len(top5_referee_fixture_valid)
    top5_referee_profile_invalid = len(top5_referee_profiles) - len(top5_referee_profile_valid)
    top5_referee_team_split_invalid = len(top5_referee_team_splits) - len(top5_referee_team_split_valid)
    top5_referee_state_captured = [
        row for row in top5_referee_state
        if sval(row, "provider_league_id")
        and sval(row, "season")
        and sval(row, "status").upper() == "CAPTURED"
    ]
    top5_referee_meta_valid = bool(
        top5_referee_meta
        and top5_referee_meta.get("status") == "OK"
        and int(top5_referee_meta.get("expected_queries") or 0) == 45
        and int(top5_referee_meta.get("captured_queries") or 0) == 45
        and int(top5_referee_meta.get("pending_or_error_queries") or 0) == 0
        and int(top5_referee_meta.get("archive_rows") or 0) == len(top5_referee_fixture_valid)
        and int(top5_referee_meta.get("profile_rows") or 0) == len(top5_referee_profile_valid)
        and int(top5_referee_meta.get("team_split_rows") or 0) == len(top5_referee_team_split_valid)
        and len(top5_referee_state_captured) == 45
        and top5_referee_meta.get("research_only") is True
        and top5_referee_meta.get("operational_betting_authority") is False
    )
    top5_referee_rows_with_referee = sum(
        bool(sval(row, "referee")) for row in top5_referee_fixture_valid
    )
    top5_referee_coverage_pct = pct(
        top5_referee_rows_with_referee, len(top5_referee_fixture_valid)
    )

    expected_prematch_leagues = {"D1", "E0", "F1", "I1", "SP1"}
    prematch_context_valid = [
        row for row in prematch_context
        if sval(row, "historical_match_id")
        and sval(row, "league_code") in expected_prematch_leagues
        and sval(row, "season_label")
        and sval(row, "date_iso")
        and sval(row, "home_team")
        and sval(row, "away_team")
        and is_true(row.get("same_day_results_excluded"))
        and is_true(row.get("no_lookahead"))
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    prematch_context_invalid = len(prematch_context) - len(prematch_context_valid)
    prematch_context_ids = {
        sval(row, "historical_match_id")
        for row in prematch_context_valid
        if sval(row, "historical_match_id")
    }
    prematch_context_duplicate_ids = len(prematch_context_valid) - len(prematch_context_ids)
    prematch_context_league_seasons = {
        (sval(row, "league_code"), sval(row, "season_label"))
        for row in prematch_context_valid
        if sval(row, "league_code") and sval(row, "season_label")
    }
    prematch_context_meta_valid = bool(
        prematch_context_meta
        and not prematch_context_meta.get("_invalid_json")
        and prematch_context_meta.get("version") == "PBK_STAGE80_FOOTBALL_DATA_PREMATCH_CONTEXT_V1"
        and prematch_context_meta.get("status") == "OK"
        and int(prematch_context_meta.get("source_rows") or 0) == 16111
        and int(prematch_context_meta.get("output_rows") or 0) == 16111
        and int(prematch_context_meta.get("unique_historical_match_ids") or 0) == 16111
        and set(prematch_context_meta.get("league_codes") or []) == expected_prematch_leagues
        and len(prematch_context_meta.get("season_labels") or []) == 9
        and int(prematch_context_meta.get("invalid_date_rows") or 0) == 0
        and int(prematch_context_meta.get("duplicate_historical_match_ids") or 0) == 0
        and int(prematch_context_meta.get("invalid_result_rows") or 0) == 0
        and prematch_context_meta.get("same_day_results_excluded") is True
        and prematch_context_meta.get("no_lookahead") is True
        and int(prematch_context_meta.get("provider_calls") or 0) == 0
        and prematch_context_meta.get("historical_backfill_only") is True
        and prematch_context_meta.get("research_only") is True
        and prematch_context_meta.get("operational_betting_authority") is False
        and prematch_context_meta.get("creates_signal") is False
        and prematch_context_meta.get("probability_mutation") is False
        and prematch_context_meta.get("eligibility_mutation") is False
        and prematch_context_meta.get("stake_changes") is False
        and prematch_context_meta.get("forward_journal_mutation") is False
    )
    expected_factor_names = [
        "WEEKDAY","KICKOFF_LOCAL","SHORT_REST","REST_ADVANTAGE",
        "CONGESTION_7D_DIFF","TABLE_RANK_DIFF","FORM5_PPG_DIFF","VENUE_FORM5_PPG_DIFF",
    ]
    prematch_factor_valid = [
        row for row in prematch_factor_research
        if sval(row, "factor") in expected_factor_names
        and sval(row, "bucket")
        and sval(row, "scope_type") in {"ALL","LEAGUE","SEASON","LEAGUE_SEASON"}
        and sval(row, "scope_value")
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    prematch_factor_stability_valid = [
        row for row in prematch_factor_stability
        if sval(row, "factor") in expected_factor_names
        and sval(row, "bucket")
        and sval(row, "scope_type") in {"ALL","LEAGUE"}
        and sval(row, "scope_value")
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
    ]
    prematch_factor_invalid = len(prematch_factor_research) - len(prematch_factor_valid)
    prematch_factor_stability_invalid = len(prematch_factor_stability) - len(prematch_factor_stability_valid)
    prematch_factor_meta_valid = bool(
        prematch_factor_meta
        and not prematch_factor_meta.get("_invalid_json")
        and prematch_factor_meta.get("version") == "PBK_STAGE80_PREMATCH_FACTOR_RESEARCH_V1"
        and prematch_factor_meta.get("status") == "OK"
        and int(prematch_factor_meta.get("source_rows") or 0) == 16111
        and int(prematch_factor_meta.get("context_rows") or 0) == 16111
        and int(prematch_factor_meta.get("joined_rows") or 0) == 16111
        and int(prematch_factor_meta.get("invalid_context_governance_rows") or 0) == 0
        and int(prematch_factor_meta.get("source_without_context") or 0) == 0
        and int(prematch_factor_meta.get("context_without_source") or 0) == 0
        and list(prematch_factor_meta.get("factor_names") or []) == expected_factor_names
        and int(prematch_factor_meta.get("factor_profile_rows") or 0) == len(prematch_factor_valid)
        and int(prematch_factor_meta.get("season_stability_rows") or 0) == len(prematch_factor_stability_valid)
        and int(prematch_factor_meta.get("closing_1x2_matches") or 0) > 0
        and int(prematch_factor_meta.get("closing_total25_matches") or 0) > 0
        and int(prematch_factor_meta.get("provider_calls") or 0) == 0
        and prematch_factor_meta.get("research_only") is True
        and prematch_factor_meta.get("operational_betting_authority") is False
        and prematch_factor_meta.get("creates_signal") is False
        and prematch_factor_meta.get("probability_mutation") is False
        and prematch_factor_meta.get("eligibility_mutation") is False
        and prematch_factor_meta.get("stake_changes") is False
        and prematch_factor_meta.get("forward_journal_mutation") is False
    )
    expected_walkforward_targets = {"HOME","DRAW","AWAY","OVER25","UNDER25"}
    prematch_walkforward_valid = [
        row for row in prematch_walkforward
        if sval(row, "factor") in expected_factor_names
        and sval(row, "bucket")
        and sval(row, "scope_type") in {"ALL","LEAGUE"}
        and sval(row, "scope_value")
        and sval(row, "target") in expected_walkforward_targets
        and sval(row, "test_season")
        and int(fnum(row.get("train_seasons")) or 0) >= 2
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    prematch_walkforward_summary_valid = [
        row for row in prematch_walkforward_summary
        if sval(row, "factor") in expected_factor_names
        and sval(row, "bucket")
        and sval(row, "scope_type") in {"ALL","LEAGUE"}
        and sval(row, "scope_value")
        and sval(row, "target") in expected_walkforward_targets
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("promotes_factor"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    prematch_walkforward_invalid = len(prematch_walkforward) - len(prematch_walkforward_valid)
    prematch_walkforward_summary_invalid = len(prematch_walkforward_summary) - len(prematch_walkforward_summary_valid)
    prematch_walkforward_meta_valid = bool(
        prematch_walkforward_meta
        and not prematch_walkforward_meta.get("_invalid_json")
        and prematch_walkforward_meta.get("version") == "PBK_STAGE80_PREMATCH_FACTOR_WALKFORWARD_V1"
        and prematch_walkforward_meta.get("status") == "OK"
        and int(prematch_walkforward_meta.get("source_rows") or 0) == 16111
        and int(prematch_walkforward_meta.get("context_rows") or 0) == 16111
        and int(prematch_walkforward_meta.get("joined_rows") or 0) == 16111
        and int(prematch_walkforward_meta.get("invalid_context_governance_rows") or 0) == 0
        and int(prematch_walkforward_meta.get("source_without_context") or 0) == 0
        and int(prematch_walkforward_meta.get("context_without_source") or 0) == 0
        and len(prematch_walkforward_meta.get("season_labels") or []) == 9
        and set(prematch_walkforward_meta.get("targets") or []) == expected_walkforward_targets
        and int(prematch_walkforward_meta.get("fold_rows") or 0) == len(prematch_walkforward_valid)
        and int(prematch_walkforward_meta.get("summary_rows") or 0) == len(prematch_walkforward_summary_valid)
        and int(prematch_walkforward_meta.get("sample_threshold_pass_folds") or 0) > 0
        and int(prematch_walkforward_meta.get("min_prior_seasons") or 0) == 2
        and int(prematch_walkforward_meta.get("min_train_market_matches") or 0) == 100
        and int(prematch_walkforward_meta.get("min_test_market_matches") or 0) == 30
        and int(prematch_walkforward_meta.get("provider_calls") or 0) == 0
        and prematch_walkforward_meta.get("research_only") is True
        and prematch_walkforward_meta.get("operational_betting_authority") is False
        and prematch_walkforward_meta.get("creates_signal") is False
        and prematch_walkforward_meta.get("promotes_factor") is False
        and prematch_walkforward_meta.get("probability_mutation") is False
        and prematch_walkforward_meta.get("eligibility_mutation") is False
        and prematch_walkforward_meta.get("stake_changes") is False
        and prematch_walkforward_meta.get("forward_journal_mutation") is False
    )
    pbk16_catalog = data["pbk16_competition_catalog"] or []
    pbk16_fixtures = data["pbk16_competition_fixtures"] or []
    pbk16_state = data["pbk16_competition_state"] or []
    pbk16_congestion = data["pbk16_competition_congestion"] or []

    pbk16_catalog_valid = [
        row for row in pbk16_catalog
        if sval(row, "competition_role") in {"DOMESTIC_LEAGUE", "DOMESTIC_CUP", "UEFA"}
        and sval(row, "country")
        and sval(row, "slot")
        and sval(row, "canonical_name")
        and sval(row, "requested_seasons")
        and sval(row, "required") in {"true", "false"}
        and sval(row, "discovery_status") in {"RESOLVED", "UNRESOLVED"}
        and (
            sval(row, "discovery_status") != "RESOLVED"
            or (sval(row, "provider_league_id") and sval(row, "provider_name"))
        )
    ]
    pbk16_catalog_invalid = len(pbk16_catalog) - len(pbk16_catalog_valid)
    pbk16_required_unresolved = [
        row for row in pbk16_catalog_valid
        if sval(row, "required") == "true"
        and sval(row, "discovery_status") != "RESOLVED"
    ]
    pbk16_optional_unresolved = [
        row for row in pbk16_catalog_valid
        if sval(row, "required") != "true"
        and sval(row, "discovery_status") != "RESOLVED"
    ]
    pbk16_resolved_domestic_league_catalog = {
        sval(row, "provider_league_id")
        for row in pbk16_catalog_valid
        if sval(row, "competition_role") == "DOMESTIC_LEAGUE"
        and sval(row, "discovery_status") == "RESOLVED"
        and sval(row, "provider_league_id")
    }

    pbk16_fixture_valid = [
        row for row in pbk16_fixtures
        if sval(row, "fixture_id")
        and sval(row, "competition_role") in {"DOMESTIC_LEAGUE", "DOMESTIC_CUP", "UEFA"}
        and sval(row, "provider_competition_id")
        and sval(row, "season")
        and sval(row, "kickoff_utc")
        and sval(row, "home_team_id")
        and sval(row, "away_team_id")
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    pbk16_fixture_invalid = len(pbk16_fixtures) - len(pbk16_fixture_valid)
    pbk16_fixture_ids = {sval(row, "fixture_id") for row in pbk16_fixture_valid}
    pbk16_fixture_duplicate_ids = len(pbk16_fixture_valid) - len(pbk16_fixture_ids)
    pbk16_domestic_fixture_rows = [
        row for row in pbk16_fixture_valid
        if sval(row, "competition_role") == "DOMESTIC_LEAGUE"
    ]
    pbk16_domestic_anchor_league_ids = {
        sval(row, "provider_competition_id")
        for row in pbk16_domestic_fixture_rows
        if sval(row, "provider_competition_id")
    }

    pbk16_state_valid = [
        row for row in pbk16_state
        if sval(row, "provider_competition_id")
        and sval(row, "season")
        and sval(row, "competition_role") in {"DOMESTIC_LEAGUE", "DOMESTIC_CUP", "UEFA"}
        and sval(row, "status") in {"PENDING", "ERROR", "CAPTURED", "UNAVAILABLE_PROVIDER_SEASON"}
        and sval(row, "provider_season_available") in {"true", "false"}
    ]
    pbk16_state_invalid = len(pbk16_state) - len(pbk16_state_valid)
    pbk16_state_captured = sum(sval(row, "status") == "CAPTURED" for row in pbk16_state_valid)
    pbk16_state_unavailable = sum(sval(row, "status") == "UNAVAILABLE_PROVIDER_SEASON" for row in pbk16_state_valid)
    pbk16_state_pending = sum(sval(row, "status") == "PENDING" for row in pbk16_state_valid)
    pbk16_state_errors = sum(sval(row, "status") == "ERROR" for row in pbk16_state_valid)

    pbk16_congestion_valid = [
        row for row in pbk16_congestion
        if sval(row, "domestic_fixture_id")
        and sval(row, "provider_league_id")
        and sval(row, "season")
        and sval(row, "kickoff_utc")
        and sval(row, "home_team_id")
        and sval(row, "away_team_id")
        and is_true(row.get("strictly_prior_fixture_evidence_only"))
        and not is_true(row.get("future_schedule_used"))
        and is_true(row.get("no_lookahead"))
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    pbk16_congestion_invalid = len(pbk16_congestion) - len(pbk16_congestion_valid)
    pbk16_congestion_ids = {
        sval(row, "domestic_fixture_id") for row in pbk16_congestion_valid
    }
    pbk16_congestion_duplicate_ids = len(pbk16_congestion_valid) - len(pbk16_congestion_ids)

    pbk16_competition_meta_valid = bool(
        pbk16_competition_meta
        and not pbk16_competition_meta.get("_invalid_json")
        and pbk16_competition_meta.get("version") == "PBK_STAGE80_PBK16_ALL_COMPETITION_BACKFILL_V1"
        and int(pbk16_competition_meta.get("locked_national_leagues") or 0) == 16
        and pbk16_competition_meta.get("historical_backfill_only") is True
        and pbk16_competition_meta.get("research_only") is True
        and pbk16_competition_meta.get("operational_betting_authority") is False
        and pbk16_competition_meta.get("creates_signal") is False
        and pbk16_competition_meta.get("probability_mutation") is False
        and pbk16_competition_meta.get("eligibility_mutation") is False
        and pbk16_competition_meta.get("stake_changes") is False
        and pbk16_competition_meta.get("forward_journal_mutation") is False
    )
    pbk16_congestion_meta_valid = bool(
        pbk16_congestion_meta
        and not pbk16_congestion_meta.get("_invalid_json")
        and pbk16_congestion_meta.get("version") == "PBK_STAGE80_PBK16_COMPETITION_CONGESTION_V1"
        and pbk16_congestion_meta.get("strictly_prior_fixture_evidence_only") is True
        and pbk16_congestion_meta.get("future_schedule_used") is False
        and pbk16_congestion_meta.get("no_lookahead") is True
        and int(pbk16_congestion_meta.get("projection_provider_calls") or 0) == 0
        and pbk16_congestion_meta.get("historical_backfill_only") is True
        and pbk16_congestion_meta.get("research_only") is True
        and pbk16_congestion_meta.get("operational_betting_authority") is False
        and pbk16_congestion_meta.get("creates_signal") is False
        and pbk16_congestion_meta.get("probability_mutation") is False
        and pbk16_congestion_meta.get("eligibility_mutation") is False
        and pbk16_congestion_meta.get("stake_changes") is False
        and pbk16_congestion_meta.get("forward_journal_mutation") is False
    )

    pbk16_international = data["pbk16_international_window_context"] or []
    pbk16_international_valid = [
        row for row in pbk16_international
        if sval(row, "domestic_fixture_id")
        and sval(row, "provider_league_id")
        and sval(row, "season")
        and sval(row, "kickoff_utc")
        and sval(row, "home_team_id")
        and sval(row, "away_team_id")
        and sval(row, "window_reference_contract") == "NEAREST_WINDOW_RELATION_GATED_V2"
        and sval(row, "player_level_international_status") == "UNVERIFIED"
        and sval(row, "final_tournaments_included") == "false"
        and sval(row, "non_uefa_only_windows_included") == "false"
        and is_true(row.get("calendar_level_only"))
        and is_true(row.get("as_known_calendar_reference"))
        and is_true(row.get("no_match_result_dependency"))
        and is_true(row.get("no_lookahead"))
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    pbk16_international_invalid = len(pbk16_international) - len(pbk16_international_valid)
    pbk16_international_ids = {
        sval(row, "domestic_fixture_id") for row in pbk16_international_valid
    }
    pbk16_international_duplicate_ids = (
        len(pbk16_international_valid) - len(pbk16_international_ids)
    )
    pbk16_international_meta_valid = bool(
        pbk16_international_meta
        and not pbk16_international_meta.get("_invalid_json")
        and pbk16_international_meta.get("version") == "PBK_STAGE80_PBK16_INTERNATIONAL_WINDOW_CONTEXT_V2"
        and pbk16_international_meta.get("status") == "OK"
        and int(pbk16_international_meta.get("source_domestic_rows") or 0) == len(pbk16_domestic_fixture_rows)
        and int(pbk16_international_meta.get("output_rows") or 0) == len(pbk16_international_valid)
        and int(pbk16_international_meta.get("unique_domestic_fixture_ids") or 0) == len(pbk16_international_ids)
        and int(pbk16_international_meta.get("duplicate_domestic_fixture_ids") or 0) == 0
        and int(pbk16_international_meta.get("invalid_domestic_rows") or 0) == 0
        and int(pbk16_international_meta.get("domestic_anchor_league_ids") or 0) == 16
        and int(pbk16_international_meta.get("calendar_windows") or 0) == 39
        and int(pbk16_international_meta.get("calendar_sources") or 0) == 5
        and pbk16_international_meta.get("window_reference_contract") == "NEAREST_WINDOW_RELATION_GATED_V2"
        and pbk16_international_meta.get("player_level_international_status") == "UNVERIFIED"
        and pbk16_international_meta.get("player_level_callup_inference") is False
        and pbk16_international_meta.get("player_level_travel_inference") is False
        and pbk16_international_meta.get("player_level_appearance_inference") is False
        and pbk16_international_meta.get("final_tournaments_included") is False
        and pbk16_international_meta.get("non_uefa_only_windows_included") is False
        and pbk16_international_meta.get("calendar_level_only") is True
        and pbk16_international_meta.get("as_known_calendar_reference") is True
        and pbk16_international_meta.get("no_match_result_dependency") is True
        and pbk16_international_meta.get("no_lookahead") is True
        and int(pbk16_international_meta.get("provider_calls") or 0) == 0
        and pbk16_international_meta.get("historical_backfill_only") is True
        and pbk16_international_meta.get("research_only") is True
        and pbk16_international_meta.get("operational_betting_authority") is False
        and pbk16_international_meta.get("creates_signal") is False
        and pbk16_international_meta.get("probability_mutation") is False
        and pbk16_international_meta.get("eligibility_mutation") is False
        and pbk16_international_meta.get("stake_changes") is False
        and pbk16_international_meta.get("forward_journal_mutation") is False
    )

    pbk14_market_bridge = data["pbk14_market_bridge"] or []
    expected_pbk14_codes = {"E0","SP1","I1","D1","F1","SC0","N1","B1","P1","T1","AUT","DNK","NOR","POL"}
    pbk14_market_bridge_valid = [
        row for row in pbk14_market_bridge
        if sval(row, "historical_match_id")
        and sval(row, "league_code") in expected_pbk14_codes
        and sval(row, "provider_league_id")
        and sval(row, "season_start")
        and sval(row, "date_iso")
        and sval(row, "source_home_team")
        and sval(row, "source_away_team")
        and sval(row, "mapping_status") in {"AUTO","HIGH","REVIEW","UNMAPPED"}
        and sval(row, "fuzzy_string_matching_used") == "false"
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
        and (
            sval(row, "mapping_status") not in {"AUTO","HIGH"}
            or (
                sval(row, "api_fixture_id")
                and is_true(row.get("one_to_one_verified"))
                and sval(row, "home_team_map_status") in {"AUTO","HIGH"}
                and sval(row, "away_team_map_status") in {"AUTO","HIGH"}
                and sval(row, "home_team_map_method") in {
                    "CANONICAL_EXACT",
                    "SCHEDULE_SCORE_FINGERPRINT",
                    "NEAR_COMPLETE_SCHEDULE_SCORE_FINGERPRINT",
                }
                and sval(row, "away_team_map_method") in {
                    "CANONICAL_EXACT",
                    "SCHEDULE_SCORE_FINGERPRINT",
                    "NEAR_COMPLETE_SCHEDULE_SCORE_FINGERPRINT",
                }
            )
        )
    ]
    pbk14_market_bridge_invalid = len(pbk14_market_bridge) - len(pbk14_market_bridge_valid)
    pbk14_market_bridge_ids = {
        sval(row, "historical_match_id") for row in pbk14_market_bridge_valid
    }
    pbk14_market_bridge_duplicate_ids = len(pbk14_market_bridge_valid) - len(pbk14_market_bridge_ids)
    pbk14_market_bridge_mapped = [
        row for row in pbk14_market_bridge_valid
        if sval(row, "mapping_status") in {"AUTO","HIGH"}
    ]
    pbk14_market_bridge_mapped_fixture_ids = [
        sval(row, "api_fixture_id") for row in pbk14_market_bridge_mapped
    ]
    pbk14_market_bridge_duplicate_api_ids = (
        len(pbk14_market_bridge_mapped_fixture_ids)
        - len(set(pbk14_market_bridge_mapped_fixture_ids))
    )
    pbk14_market_bridge_counts = {
        status: sum(sval(row, "mapping_status") == status for row in pbk14_market_bridge_valid)
        for status in ("AUTO","HIGH","REVIEW","UNMAPPED")
    }
    pbk14_market_source_meta_valid = bool(
        pbk14_market_source_meta
        and not pbk14_market_source_meta.get("_invalid_json")
        and pbk14_market_source_meta.get("version") == "PBK_STAGE80_FOOTBALL_DATA_PBK14_HISTORY_V1"
        and int(pbk14_market_source_meta.get("expected_source_files") or 0) == 94
        and int(pbk14_market_source_meta.get("present_source_files") or 0) == 94
        and int(pbk14_market_source_meta.get("missing_source_files") or 0) == 0
        and int(pbk14_market_source_meta.get("supported_leagues") or 0) == 14
        and len(pbk14_market_source_meta.get("unsupported_pbk_leagues") or []) == 2
        and pbk14_market_source_meta.get("historical_backfill_only") is True
        and pbk14_market_source_meta.get("research_only") is True
        and pbk14_market_source_meta.get("operational_betting_authority") is False
        and pbk14_market_source_meta.get("creates_signal") is False
        and pbk14_market_source_meta.get("probability_mutation") is False
        and pbk14_market_source_meta.get("eligibility_mutation") is False
        and pbk14_market_source_meta.get("stake_changes") is False
        and pbk14_market_source_meta.get("forward_journal_mutation") is False
    )
    pbk14_market_bridge_meta_valid = bool(
        pbk14_market_bridge_meta
        and not pbk14_market_bridge_meta.get("_invalid_json")
        and pbk14_market_bridge_meta.get("version") == "PBK_STAGE80_PBK14_FIXTURE_BRIDGE_V2_NEAR_COMPLETE"
        and int(pbk14_market_bridge_meta.get("source_rows") or 0) == len(pbk14_market_bridge)
        and int(pbk14_market_bridge_meta.get("mapped_auto") or 0) == pbk14_market_bridge_counts["AUTO"]
        and int(pbk14_market_bridge_meta.get("mapped_high") or 0) == pbk14_market_bridge_counts["HIGH"]
        and int(pbk14_market_bridge_meta.get("review") or 0) == pbk14_market_bridge_counts["REVIEW"]
        and int(pbk14_market_bridge_meta.get("unmapped") or 0) == pbk14_market_bridge_counts["UNMAPPED"]
        and int(pbk14_market_bridge_meta.get("duplicate_mapped_api_fixture_ids") or 0) == 0
        and (pbk14_market_bridge_meta.get("mapping_policy") or {}).get("fuzzy_string_matching_used") is False
        and (pbk14_market_bridge_meta.get("mapping_policy") or {}).get("review_unmapped_excluded") is True
        and (pbk14_market_bridge_meta.get("mapping_policy") or {}).get("final_score_identity_only") is True
        and (pbk14_market_bridge_meta.get("mapping_policy") or {}).get("source_aliases_may_share_provider_team_if_fixture_evidence_is_disjoint") is True
        and float(((pbk14_market_bridge_meta.get("mapping_policy") or {}).get("near_complete_thresholds") or {}).get("min_source_ratio") or 0) >= 0.88
        and pbk14_market_bridge_meta.get("historical_backfill_only") is True
        and pbk14_market_bridge_meta.get("research_only") is True
        and pbk14_market_bridge_meta.get("operational_betting_authority") is False
        and pbk14_market_bridge_meta.get("creates_signal") is False
        and pbk14_market_bridge_meta.get("probability_mutation") is False
        and pbk14_market_bridge_meta.get("eligibility_mutation") is False
        and pbk14_market_bridge_meta.get("stake_changes") is False
        and pbk14_market_bridge_meta.get("forward_journal_mutation") is False
    )

    pbk14_international_join = data["pbk14_international_window_market_join"] or []
    pbk14_international_join_valid = [
        row for row in pbk14_international_join
        if sval(row, "historical_match_id")
        and sval(row, "api_fixture_id")
        and sval(row, "mapping_status") in {"AUTO","HIGH"}
        and sval(row, "fuzzy_string_matching_used") == "false"
        and is_true(row.get("one_to_one_verified"))
        and sval(row, "player_level_international_status") == "UNVERIFIED"
        and sval(row, "final_tournaments_included") == "false"
        and sval(row, "non_uefa_only_windows_included") == "false"
        and is_true(row.get("calendar_level_only"))
        and is_true(row.get("as_known_calendar_reference"))
        and is_true(row.get("no_match_result_dependency"))
        and is_true(row.get("no_lookahead"))
        and sval(row, "context_provider_calls") == "0"
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    pbk14_international_join_invalid = len(pbk14_international_join) - len(pbk14_international_join_valid)
    pbk14_international_join_hist_ids = {
        sval(row, "historical_match_id") for row in pbk14_international_join_valid
    }
    pbk14_international_join_api_ids = {
        sval(row, "api_fixture_id") for row in pbk14_international_join_valid
    }
    pbk14_international_join_duplicate_hist_ids = (
        len(pbk14_international_join_valid) - len(pbk14_international_join_hist_ids)
    )
    pbk14_international_join_duplicate_api_ids = (
        len(pbk14_international_join_valid) - len(pbk14_international_join_api_ids)
    )
    pbk14_international_join_meta_valid = bool(
        pbk14_international_join_meta
        and not pbk14_international_join_meta.get("_invalid_json")
        and pbk14_international_join_meta.get("version") == "PBK_STAGE80_PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_V1"
        and int(pbk14_international_join_meta.get("joined_rows") or 0) == len(pbk14_international_join_valid)
        and int(pbk14_international_join_meta.get("missing_market_rows") or 0) == 0
        and int(pbk14_international_join_meta.get("missing_context_rows") or 0) == 0
        and int(pbk14_international_join_meta.get("bridge_eligible_duplicate_historical_ids") or 0) == 0
        and int(pbk14_international_join_meta.get("bridge_eligible_duplicate_api_fixture_ids") or 0) == 0
        and int(pbk14_international_join_meta.get("context_invalid_rows") or 0) == 0
        and int(pbk14_international_join_meta.get("context_duplicate_fixture_ids") or 0) == 0
        and float(pbk14_international_join_meta.get("join_coverage_pct") or 0) == 100.0
        and pbk14_international_join_meta.get("player_level_international_status") == "UNVERIFIED"
        and pbk14_international_join_meta.get("player_callup_inferred") is False
        and pbk14_international_join_meta.get("player_travel_inferred") is False
        and pbk14_international_join_meta.get("player_appearance_inferred") is False
        and pbk14_international_join_meta.get("review_unmapped_excluded") is True
        and pbk14_international_join_meta.get("fuzzy_string_matching_used") is False
        and pbk14_international_join_meta.get("calendar_level_only") is True
        and pbk14_international_join_meta.get("as_known_calendar_reference") is True
        and pbk14_international_join_meta.get("no_match_result_dependency") is True
        and pbk14_international_join_meta.get("no_lookahead") is True
        and int(pbk14_international_join_meta.get("provider_calls") or 0) == 0
        and pbk14_international_join_meta.get("research_only") is True
        and pbk14_international_join_meta.get("operational_betting_authority") is False
        and pbk14_international_join_meta.get("creates_signal") is False
        and pbk14_international_join_meta.get("probability_mutation") is False
        and pbk14_international_join_meta.get("eligibility_mutation") is False
        and pbk14_international_join_meta.get("stake_changes") is False
        and pbk14_international_join_meta.get("forward_journal_mutation") is False
    )

    pbk14_congestion_join = data["pbk14_congestion_market_join"] or []
    pbk14_congestion_profiles = data["pbk14_congestion_market_profiles"] or []
    pbk14_congestion_stability = data["pbk14_congestion_market_stability"] or []
    expected_congestion_factors = {
        "NONLEAGUE_72H_SIDE","NONLEAGUE_96H_SIDE",
        "UEFA_72H_SIDE","UEFA_96H_SIDE",
        "DOMESTIC_CUP_72H_SIDE","DOMESTIC_CUP_96H_SIDE",
        "PREV_NONLEAGUE_THURSDAY_SIDE","THURSDAY_TO_WEEKEND_SIDE",
    }

    pbk14_congestion_join_valid = [
        row for row in pbk14_congestion_join
        if sval(row, "historical_match_id")
        and sval(row, "api_fixture_id")
        and sval(row, "mapping_status") in {"AUTO","HIGH"}
        and sval(row, "fuzzy_string_matching_used") == "false"
        and is_true(row.get("one_to_one_verified"))
        and is_true(row.get("strictly_prior_fixture_evidence_only"))
        and not is_true(row.get("future_schedule_used"))
        and is_true(row.get("no_lookahead"))
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    pbk14_congestion_join_invalid = len(pbk14_congestion_join) - len(pbk14_congestion_join_valid)
    pbk14_congestion_join_hist_ids = {sval(row, "historical_match_id") for row in pbk14_congestion_join_valid}
    pbk14_congestion_join_api_ids = {sval(row, "api_fixture_id") for row in pbk14_congestion_join_valid}
    pbk14_congestion_join_duplicate_hist_ids = len(pbk14_congestion_join_valid) - len(pbk14_congestion_join_hist_ids)
    pbk14_congestion_join_duplicate_api_ids = len(pbk14_congestion_join_valid) - len(pbk14_congestion_join_api_ids)

    pbk14_congestion_join_meta_valid = bool(
        pbk14_congestion_join_meta
        and not pbk14_congestion_join_meta.get("_invalid_json")
        and pbk14_congestion_join_meta.get("version") == "PBK_STAGE80_PBK14_CONGESTION_MARKET_JOIN_V1"
        and int(pbk14_congestion_join_meta.get("joined_rows") or 0) == len(pbk14_congestion_join_valid)
        and int(pbk14_congestion_join_meta.get("missing_market_rows") or 0) == 0
        and int(pbk14_congestion_join_meta.get("missing_congestion_rows") or 0) == 0
        and int(pbk14_congestion_join_meta.get("bridge_eligible_duplicate_historical_ids") or 0) == 0
        and int(pbk14_congestion_join_meta.get("bridge_eligible_duplicate_api_fixture_ids") or 0) == 0
        and int(pbk14_congestion_join_meta.get("congestion_duplicate_fixture_ids") or 0) == 0
        and float(pbk14_congestion_join_meta.get("join_coverage_pct") or 0) == 100.0
        and pbk14_congestion_join_meta.get("review_unmapped_excluded") is True
        and pbk14_congestion_join_meta.get("fuzzy_string_matching_used") is False
        and pbk14_congestion_join_meta.get("strictly_prior_fixture_evidence_only") is True
        and pbk14_congestion_join_meta.get("future_schedule_used") is False
        and pbk14_congestion_join_meta.get("no_lookahead") is True
        and int(pbk14_congestion_join_meta.get("provider_calls") or 0) == 0
        and pbk14_congestion_join_meta.get("research_only") is True
        and pbk14_congestion_join_meta.get("operational_betting_authority") is False
        and pbk14_congestion_join_meta.get("creates_signal") is False
        and pbk14_congestion_join_meta.get("probability_mutation") is False
        and pbk14_congestion_join_meta.get("eligibility_mutation") is False
        and pbk14_congestion_join_meta.get("stake_changes") is False
        and pbk14_congestion_join_meta.get("forward_journal_mutation") is False
    )

    pbk14_congestion_profiles_valid = [
        row for row in pbk14_congestion_profiles
        if sval(row, "factor") in expected_congestion_factors
        and sval(row, "bucket")
        and sval(row, "scope_type") in {"ALL","LEAGUE","SEASON","LEAGUE_SEASON"}
        and sval(row, "scope_value")
        and fnum(row.get("matches")) is not None
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("promotes_factor"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    pbk14_congestion_profiles_invalid = len(pbk14_congestion_profiles) - len(pbk14_congestion_profiles_valid)

    pbk14_congestion_stability_valid = [
        row for row in pbk14_congestion_stability
        if sval(row, "factor") in expected_congestion_factors
        and sval(row, "bucket")
        and sval(row, "scope_type") in {"ALL","LEAGUE"}
        and sval(row, "scope_value")
        and fnum(row.get("seasons_with_matches")) is not None
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("promotes_factor"))
    ]
    pbk14_congestion_stability_invalid = len(pbk14_congestion_stability) - len(pbk14_congestion_stability_valid)

    pbk14_congestion_research_meta_valid = bool(
        pbk14_congestion_research_meta
        and not pbk14_congestion_research_meta.get("_invalid_json")
        and pbk14_congestion_research_meta.get("version") == "PBK_STAGE80_PBK14_CONGESTION_MARKET_RESEARCH_V1"
        and int(pbk14_congestion_research_meta.get("source_rows") or 0) == len(pbk14_congestion_join_valid)
        and int(pbk14_congestion_research_meta.get("valid_research_rows") or 0) == len(pbk14_congestion_join_valid)
        and int(pbk14_congestion_research_meta.get("invalid_governance_or_result_rows") or 0) == 0
        and set(pbk14_congestion_research_meta.get("factor_names") or []) == expected_congestion_factors
        and int(pbk14_congestion_research_meta.get("factor_profile_rows") or 0) == len(pbk14_congestion_profiles_valid)
        and int(pbk14_congestion_research_meta.get("stability_rows") or 0) == len(pbk14_congestion_stability_valid)
        and pbk14_congestion_research_meta.get("market_novig_is_pbk_probability") is False
        and pbk14_congestion_research_meta.get("strictly_prior_fixture_evidence_only") is True
        and pbk14_congestion_research_meta.get("future_schedule_used") is False
        and pbk14_congestion_research_meta.get("no_lookahead") is True
        and int(pbk14_congestion_research_meta.get("provider_calls") or 0) == 0
        and pbk14_congestion_research_meta.get("research_only") is True
        and pbk14_congestion_research_meta.get("operational_betting_authority") is False
        and pbk14_congestion_research_meta.get("creates_signal") is False
        and pbk14_congestion_research_meta.get("promotes_factor") is False
        and pbk14_congestion_research_meta.get("probability_mutation") is False
        and pbk14_congestion_research_meta.get("eligibility_mutation") is False
        and pbk14_congestion_research_meta.get("stake_changes") is False
        and pbk14_congestion_research_meta.get("forward_journal_mutation") is False
    )

    pbk14_congestion_walkforward = data["pbk14_congestion_market_walkforward"] or []
    pbk14_congestion_walkforward_summary = data["pbk14_congestion_market_walkforward_summary"] or []

    pbk14_congestion_walkforward_valid = [
        row for row in pbk14_congestion_walkforward
        if sval(row, "factor") in expected_congestion_factors
        and sval(row, "bucket")
        and sval(row, "scope_type") in {"ALL","LEAGUE"}
        and sval(row, "scope_value")
        and sval(row, "target") in {"HOME","DRAW","AWAY","OVER25","UNDER25"}
        and sval(row, "test_season")
        and fnum(row.get("train_seasons")) is not None
        and fnum(row.get("train_market_matches")) is not None
        and fnum(row.get("test_market_matches")) is not None
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("promotes_factor"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    pbk14_congestion_walkforward_invalid = (
        len(pbk14_congestion_walkforward) - len(pbk14_congestion_walkforward_valid)
    )
    pbk14_congestion_walkforward_temporal_invalid = sum(
        1 for row in pbk14_congestion_walkforward_valid
        if (
            fnum(row.get("train_last_season")) is None
            or fnum(row.get("test_season")) is None
            or int(float(row["train_last_season"])) >= int(float(row["test_season"]))
        )
    )

    pbk14_congestion_walkforward_summary_valid = [
        row for row in pbk14_congestion_walkforward_summary
        if sval(row, "factor") in expected_congestion_factors
        and sval(row, "bucket")
        and sval(row, "scope_type") in {"ALL","LEAGUE"}
        and sval(row, "scope_value")
        and sval(row, "target") in {"HOME","DRAW","AWAY","OVER25","UNDER25"}
        and fnum(row.get("folds")) is not None
        and fnum(row.get("sample_threshold_pass_folds")) is not None
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("promotes_factor"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    ]
    pbk14_congestion_walkforward_summary_invalid = (
        len(pbk14_congestion_walkforward_summary)
        - len(pbk14_congestion_walkforward_summary_valid)
    )

    pbk14_congestion_walkforward_meta_valid = bool(
        pbk14_congestion_walkforward_meta
        and not pbk14_congestion_walkforward_meta.get("_invalid_json")
        and pbk14_congestion_walkforward_meta.get("version") == "PBK_STAGE80_PBK14_CONGESTION_MARKET_WALKFORWARD_V1"
        and pbk14_congestion_walkforward_meta.get("status") == "OK"
        and int(pbk14_congestion_walkforward_meta.get("source_rows") or 0) == len(pbk14_congestion_join_valid)
        and int(pbk14_congestion_walkforward_meta.get("valid_research_rows") or 0) == len(pbk14_congestion_join_valid)
        and int(pbk14_congestion_walkforward_meta.get("invalid_governance_or_result_rows") or 0) == 0
        and len(pbk14_congestion_walkforward_meta.get("season_starts") or []) == 9
        and set(pbk14_congestion_walkforward_meta.get("factor_names") or []) == expected_congestion_factors
        and set(pbk14_congestion_walkforward_meta.get("targets") or []) == {"HOME","DRAW","AWAY","OVER25","UNDER25"}
        and int(pbk14_congestion_walkforward_meta.get("fold_rows") or 0) == len(pbk14_congestion_walkforward_valid)
        and int(pbk14_congestion_walkforward_meta.get("summary_rows") or 0) == len(pbk14_congestion_walkforward_summary_valid)
        and int(pbk14_congestion_walkforward_meta.get("sample_threshold_pass_folds") or 0) > 0
        and int(pbk14_congestion_walkforward_meta.get("min_prior_seasons") or 0) == 2
        and int(pbk14_congestion_walkforward_meta.get("min_train_market_matches") or 0) == 100
        and int(pbk14_congestion_walkforward_meta.get("min_test_market_matches") or 0) == 30
        and pbk14_congestion_walkforward_meta.get("strictly_prior_fixture_evidence_only") is True
        and pbk14_congestion_walkforward_meta.get("future_schedule_used") is False
        and pbk14_congestion_walkforward_meta.get("no_lookahead") is True
        and int(pbk14_congestion_walkforward_meta.get("provider_calls") or 0) == 0
        and pbk14_congestion_walkforward_meta.get("research_only") is True
        and pbk14_congestion_walkforward_meta.get("operational_betting_authority") is False
        and pbk14_congestion_walkforward_meta.get("creates_signal") is False
        and pbk14_congestion_walkforward_meta.get("promotes_factor") is False
        and pbk14_congestion_walkforward_meta.get("probability_mutation") is False
        and pbk14_congestion_walkforward_meta.get("eligibility_mutation") is False
        and pbk14_congestion_walkforward_meta.get("stake_changes") is False
        and pbk14_congestion_walkforward_meta.get("forward_journal_mutation") is False
    )

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
    if data["referee_profiles"] is None or data["referee_team_splits"] is None or referee_meta is None:
        gaps.append("REFEREE_RESEARCH_NOT_MATERIALIZED")
    elif not referee_meta_valid or referee_profile_invalid or referee_team_split_invalid:
        gaps.append("REFEREE_RESEARCH_INVALID")
    if (
        data["top5_referee_fixtures"] is None
        or data["top5_referee_profiles"] is None
        or data["top5_referee_team_splits"] is None
        or data["top5_referee_state"] is None
        or top5_referee_meta is None
    ):
        gaps.append("REFEREE_HISTORY_TOP5_BACKFILL_NOT_MATERIALIZED")
        gaps.append("REFEREE_HISTORY_TOP5_PARTIAL_EPL_ONLY")
    elif (
        top5_referee_fixture_invalid
        or top5_referee_profile_invalid
        or top5_referee_team_split_invalid
        or not top5_referee_meta_valid
    ):
        gaps.append("REFEREE_HISTORY_TOP5_BACKFILL_INVALID_OR_INCOMPLETE")
        gaps.append("REFEREE_HISTORY_TOP5_PARTIAL_EPL_ONLY")
    elif (
        top5_referee_coverage_pct is not None
        and top5_referee_coverage_pct < 100.0
    ):
        gaps.append("REFEREE_HISTORY_TOP5_PROVIDER_REFEREE_FIELD_PARTIAL")
    if data["prematch_context"] is None or prematch_context_meta is None:
        gaps.append("PREMATCH_CONTEXT_TOP5_NOT_MATERIALIZED")
    elif (
        not prematch_context_meta_valid
        or prematch_context_invalid
        or prematch_context_duplicate_ids
        or len(prematch_context_valid) != 16111
        or len(prematch_context_ids) != 16111
        or len(prematch_context_league_seasons) != 45
    ):
        gaps.append("PREMATCH_CONTEXT_TOP5_INVALID_OR_INCOMPLETE")
    if (
        data["prematch_factor_research"] is None
        or data["prematch_factor_stability"] is None
        or prematch_factor_meta is None
    ):
        gaps.append("PREMATCH_FACTOR_RESEARCH_NOT_MATERIALIZED")
    elif (
        not prematch_factor_meta_valid
        or prematch_factor_invalid
        or prematch_factor_stability_invalid
        or not prematch_factor_valid
        or not prematch_factor_stability_valid
    ):
        gaps.append("PREMATCH_FACTOR_RESEARCH_INVALID_OR_INCOMPLETE")
    if (
        data["prematch_walkforward"] is None
        or data["prematch_walkforward_summary"] is None
        or prematch_walkforward_meta is None
    ):
        gaps.append("PREMATCH_FACTOR_WALKFORWARD_NOT_MATERIALIZED")
    elif (
        not prematch_walkforward_meta_valid
        or prematch_walkforward_invalid
        or prematch_walkforward_summary_invalid
        or not prematch_walkforward_valid
        or not prematch_walkforward_summary_valid
    ):
        gaps.append("PREMATCH_FACTOR_WALKFORWARD_INVALID_OR_INCOMPLETE")
    if (
        data["pbk16_competition_catalog"] is None
        or data["pbk16_competition_fixtures"] is None
        or data["pbk16_competition_state"] is None
        or pbk16_competition_meta is None
    ):
        gaps.append("PBK16_COMPETITION_HISTORY_NOT_MATERIALIZED")
    else:
        if (
            pbk16_catalog_invalid
            or pbk16_fixture_invalid
            or pbk16_fixture_duplicate_ids
            or pbk16_state_invalid
            or not pbk16_competition_meta_valid
        ):
            gaps.append("PBK16_COMPETITION_HISTORY_INVALID")
        if pbk16_required_unresolved:
            gaps.append("PBK16_COMPETITION_DISCOVERY_REQUIRED_UNRESOLVED")
        if pbk16_state_unavailable:
            gaps.append("PBK16_COMPETITION_PROVIDER_SEASONS_PARTIAL")
        if pbk16_state_pending:
            gaps.append("PBK16_COMPETITION_BACKFILL_PENDING")
        if pbk16_state_errors:
            gaps.append("PBK16_COMPETITION_BACKFILL_ERRORS")
        if len(pbk16_resolved_domestic_league_catalog) < 16 or len(pbk16_domestic_anchor_league_ids) < 16:
            gaps.append("PBK16_DOMESTIC_ANCHOR_LEAGUE_COVERAGE_PARTIAL")
    if data["pbk16_competition_congestion"] is None or pbk16_congestion_meta is None:
        gaps.append("PBK16_COMPETITION_CONGESTION_NOT_MATERIALIZED")
    elif (
        pbk16_congestion_invalid
        or pbk16_congestion_duplicate_ids
        or not pbk16_congestion_meta_valid
        or len(pbk16_congestion_valid) != len(pbk16_domestic_fixture_rows)
        or pbk16_congestion_ids != {
            sval(row, "fixture_id") for row in pbk16_domestic_fixture_rows
        }
    ):
        gaps.append("PBK16_COMPETITION_CONGESTION_INVALID")
    if data["pbk16_international_window_context"] is None or pbk16_international_meta is None:
        gaps.append("PBK16_INTERNATIONAL_WINDOW_CONTEXT_NOT_MATERIALIZED")
    elif (
        pbk16_international_invalid
        or pbk16_international_duplicate_ids
        or not pbk16_international_meta_valid
        or len(pbk16_international_valid) != len(pbk16_domestic_fixture_rows)
        or pbk16_international_ids != {
            sval(row, "fixture_id") for row in pbk16_domestic_fixture_rows
        }
    ):
        gaps.append("PBK16_INTERNATIONAL_WINDOW_CONTEXT_INVALID")
    if (
        data["pbk14_market_bridge"] is None
        or pbk14_market_source_meta is None
        or pbk14_market_bridge_meta is None
    ):
        gaps.append("PBK14_HISTORICAL_MARKET_BRIDGE_NOT_MATERIALIZED")
    else:
        if (
            pbk14_market_bridge_invalid
            or pbk14_market_bridge_duplicate_ids
            or pbk14_market_bridge_duplicate_api_ids
            or not pbk14_market_source_meta_valid
            or not pbk14_market_bridge_meta_valid
        ):
            gaps.append("PBK14_HISTORICAL_MARKET_BRIDGE_INVALID")
        if pbk14_market_bridge_counts["REVIEW"] or pbk14_market_bridge_counts["UNMAPPED"]:
            gaps.append("PBK14_HISTORICAL_MARKET_BRIDGE_PARTIAL_MAPPING")
        gaps.append("PBK16_HISTORICAL_MARKET_SOURCE_LIMITED_TO_14_LEAGUES")
    if data["pbk14_international_window_market_join"] is None or pbk14_international_join_meta is None:
        gaps.append("PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_NOT_MATERIALIZED")
    elif (
        pbk14_international_join_invalid
        or pbk14_international_join_duplicate_hist_ids
        or pbk14_international_join_duplicate_api_ids
        or not pbk14_international_join_meta_valid
    ):
        gaps.append("PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_INVALID")
    if data["pbk14_congestion_market_join"] is None or pbk14_congestion_join_meta is None:
        gaps.append("PBK14_CONGESTION_MARKET_JOIN_NOT_MATERIALIZED")
    elif (
        pbk14_congestion_join_invalid
        or pbk14_congestion_join_duplicate_hist_ids
        or pbk14_congestion_join_duplicate_api_ids
        or not pbk14_congestion_join_meta_valid
    ):
        gaps.append("PBK14_CONGESTION_MARKET_JOIN_INVALID")
    if (
        data["pbk14_congestion_market_profiles"] is None
        or data["pbk14_congestion_market_stability"] is None
        or pbk14_congestion_research_meta is None
    ):
        gaps.append("PBK14_CONGESTION_MARKET_RESEARCH_NOT_MATERIALIZED")
    elif (
        pbk14_congestion_profiles_invalid
        or pbk14_congestion_stability_invalid
        or not pbk14_congestion_profiles_valid
        or not pbk14_congestion_stability_valid
        or not pbk14_congestion_research_meta_valid
    ):
        gaps.append("PBK14_CONGESTION_MARKET_RESEARCH_INVALID")
    if (
        data["pbk14_congestion_market_walkforward"] is None
        or data["pbk14_congestion_market_walkforward_summary"] is None
        or pbk14_congestion_walkforward_meta is None
    ):
        gaps.append("PBK14_CONGESTION_MARKET_WALKFORWARD_NOT_MATERIALIZED")
    elif (
        pbk14_congestion_walkforward_invalid
        or pbk14_congestion_walkforward_summary_invalid
        or pbk14_congestion_walkforward_temporal_invalid
        or not pbk14_congestion_walkforward_valid
        or not pbk14_congestion_walkforward_summary_valid
        or not pbk14_congestion_walkforward_meta_valid
    ):
        gaps.append("PBK14_CONGESTION_MARKET_WALKFORWARD_INVALID")
    if data["lineup_archive"] is None:
        gaps.append("LINEUP_ARCHIVE_WAITING_FIRST_BUILD")
    if data["injury_archive"] is None:
        gaps.append("INJURY_ARCHIVE_WAITING_FIRST_BUILD")
    if not raw_archive["configured"]:
        gaps.append("RAW_ARCHIVE_DURABLE_STORAGE_NOT_CONFIGURED")
    elif raw_archive["status"] != "OK":
        gaps.append("RAW_ARCHIVE_STORAGE_NEEDS_ATTENTION")
    gaps.append("MATCH_CONTEXT_COVERAGE_IS_CANONICAL_SCOPE_ONLY")
    if data["player_profiles"] is None or not player_profile_valid:
        gaps.append("PLAYER_PROFILE_EVIDENCE_NOT_MATERIALIZED")
    elif current_roster_player_ids and len(current_roster_player_ids & player_profile_ids) < len(current_roster_player_ids):
        gaps.append("PLAYER_PROFILE_PARTIAL_CURRENT_ROSTER_COVERAGE")
    if player_profile_invalid:
        gaps.append("PLAYER_PROFILE_INVALID_ROWS")
    if data["transfer_identity"] is None or not transfer_identity_valid:
        gaps.append("VERIFIED_TRANSFER_IDENTITY_NOT_MATERIALIZED")
    if transfer_identity_invalid:
        gaps.append("TRANSFER_IDENTITY_INVALID_ROWS")
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
    if data["player_xg_xa_research"] is None and not stage91_external_payload_attested:
        gaps.append("PLAYER_XG_XA_RESEARCH_SOURCE_NOT_MATERIALIZED")
    elif data["player_xg_xa_research"] is not None and not player_xg_xa_valid:
        gaps.append("PLAYER_XG_XA_RESEARCH_SOURCE_INVALID")
    elif data["player_xg_xa_mapping"] is None or data["player_xg_xa_mapped"] is None:
        gaps.append("PLAYER_XG_XA_PBK_IDENTITY_MAPPING_NOT_MATERIALIZED")
    elif not player_xg_xa_auto_mapping or not player_xg_xa_mapped_valid:
        gaps.append("PLAYER_XG_XA_NO_HIGH_CONFIDENCE_PBK_MAPPING")
    if player_xg_xa_invalid:
        gaps.append("PLAYER_XG_XA_RESEARCH_SOURCE_INVALID_ROWS")
    if player_xg_xa_mapped_invalid:
        gaps.append("PLAYER_XG_XA_MAPPED_RESEARCH_INVALID_ROWS")

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
            "player_xg_xa_source_payload_in_repository": data["player_xg_xa_research"] is not None,
            "player_xg_xa_stage91_meta_present": stage91_meta is not None,
            "player_xg_xa_stage91_meta_valid": stage91_meta_valid,
            "player_xg_xa_stage91_attested_rows": int(stage91_meta.get("player_match_rows") or 0) if stage91_meta_valid else 0,
            "player_xg_xa_stage91_attested_unique_players": int(stage91_meta.get("unique_statsbomb_players") or 0) if stage91_meta_valid else 0,
            "player_xg_xa_stage91_source_revision": str(stage91_meta.get("source_revision") or "") if stage91_meta_valid else "",
            "player_xg_xa_research_rows": len(player_xg_xa_valid),
            "player_xg_xa_research_invalid_rows": player_xg_xa_invalid,
            "player_xg_xa_research_matches": len(player_xg_xa_matches),
            "player_xg_xa_research_unique_players": len(player_xg_xa_players),
            "player_xg_source": "StatsBomb Open Data shot.statsbomb_xg when Stage91 is materialized",
            "player_xa_method": "Derived by joining pass event id to shot.key_pass_id and assigning the created shot xG",
            "player_xg_xa_attribution_required": True,
            "player_xg_xa_operational_authority": False,
            "player_xg_xa_pbk_identity_mapping": player_xg_xa_mapping_status,
            "player_xg_xa_mapping_rows": len(player_xg_xa_mapping),
            "player_xg_xa_auto_high_mappings": len(player_xg_xa_auto_mapping),
            "player_xg_xa_review_mappings": len(player_xg_xa_review_mapping),
            "player_xg_xa_mapped_research_rows": len(player_xg_xa_mapped_valid),
            "player_xg_xa_mapped_research_invalid_rows": player_xg_xa_mapped_invalid,
            "player_xg_xa_mapped_pbk_players": len(player_xg_xa_mapped_players),
            "player_xg_xa_mapped_matches": len(player_xg_xa_mapped_matches),
            "player_xg_xa_evidence_note": "Stage91 provides StatsBomb research metrics. The large Stage91 source payload may remain external/local when an OK Stage91 meta attestation plus valid Stage92 AUTO/HIGH mapped rows are persisted; this never implies the source CSV is stored in Git. Stage92 maps only exact full names through the verified Transfermarkt→PBK bridge; abbreviated-name candidates remain REVIEW and never enter mapped research. Mapped xG/xA remains research-only and non-operational.",
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
        "player_profiles": {
            "present": data["player_profiles"] is not None,
            "rows": len(player_profiles),
            "valid_rows": len(player_profile_valid),
            "team_source_rows": player_profile_team_source_rows,
            "residual_player_id_source_rows": player_profile_residual_source_rows,
            "identity_ready_rows": len(player_profile_identity_ready),
            "invalid_rows": player_profile_invalid,
            "unique_players": len(player_profile_ids),
            "identity_ready_unique_players": len(player_profile_identity_ready_ids),
            "unique_teams": len(player_profile_team_ids),
            "current_roster_player_coverage_pct": pct(
                len(current_roster_player_ids & player_profile_ids),
                len(current_roster_player_ids),
            ),
            "identity_ready_current_roster_coverage_pct": pct(
                len(current_roster_player_ids & player_profile_identity_ready_ids),
                len(current_roster_player_ids),
            ),
            "evidence_note": "Bounded API-Football player profile evidence from team+season plus residual player-id+season calls. Residual team context is taken from the current PBK roster, not inferred from season statistics. Full-name+DOB+club may support conservative cross-provider identity mapping; this never grants betting/model authority.",
        },
        "transfer_identity": {
            "present": data["transfer_identity"] is not None,
            "rows": len(transfer_identity),
            "valid_rows": len(transfer_identity_valid),
            "invalid_rows": transfer_identity_invalid,
            "unique_pbk_players": len(transfer_identity_pbk_players),
            "unique_transfermarkt_players": len(transfer_identity_tm_players),
            "approved_methods": ["EXACT_NAME_CURRENT_CLUB", "EXACT_PROFILE_NAME_DOB_CURRENT_CLUB", "EXACT_STATS_NAME_CURRENT_CLUB"],
            "evidence_note": "Durable identity bridge independent of whether a player has any transfer-event rows; HIGH/AUTO only and research/enrichment authority only.",
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
            "evidence_note": "Durable transfer events count only when linked by an approved HIGH-confidence exact-name+club identity method; this is historical enrichment, not current squad authority.",
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
        "referee_research": {
            "profiles_present": data["referee_profiles"] is not None,
            "team_splits_present": data["referee_team_splits"] is not None,
            "meta_present": referee_meta is not None,
            "meta_valid": referee_meta_valid,
            "profile_rows": len(referee_profiles),
            "valid_profile_rows": len(referee_profile_valid),
            "invalid_profile_rows": referee_profile_invalid,
            "unique_referees": len({sval(row, "referee") for row in referee_profile_valid}),
            "team_split_rows": len(referee_team_splits),
            "valid_team_split_rows": len(referee_team_split_valid),
            "invalid_team_split_rows": referee_team_split_invalid,
            "unique_teams": len({sval(row, "team") for row in referee_team_split_valid}),
            "source_matches": int(referee_meta.get("source_rows") or 0) if referee_meta_valid else None,
            "source_scope": "EPL_ONLY",
            "penalties_available": False,
            "operational_betting_authority": False,
            "evidence_note": "Derived from the Football-Data EPL-only 2017/18-2025/26 referee slice. Descriptive historical aggregates only; missing Top-5 leagues remain UNKNOWN and no observed split is treated as referee bias or causation.",
        },
        "referee_top5_backfill": {
            "fixture_archive_present": data["top5_referee_fixtures"] is not None,
            "profiles_present": data["top5_referee_profiles"] is not None,
            "team_splits_present": data["top5_referee_team_splits"] is not None,
            "state_present": data["top5_referee_state"] is not None,
            "meta_present": top5_referee_meta is not None,
            "meta_valid": top5_referee_meta_valid,
            "fixture_rows": len(top5_referee_fixtures),
            "valid_fixture_rows": len(top5_referee_fixture_valid),
            "invalid_fixture_rows": top5_referee_fixture_invalid,
            "rows_with_referee": top5_referee_rows_with_referee,
            "referee_coverage_pct": top5_referee_coverage_pct,
            "profile_rows": len(top5_referee_profiles),
            "valid_profile_rows": len(top5_referee_profile_valid),
            "team_split_rows": len(top5_referee_team_splits),
            "valid_team_split_rows": len(top5_referee_team_split_valid),
            "captured_league_seasons": len(top5_referee_state_captured),
            "expected_league_seasons": 45,
            "source_scope": "TOP5_9_SEASONS_API_FOOTBALL",
            "cards_available": False,
            "fouls_available": False,
            "penalties_available": False,
            "operational_betting_authority": False,
            "evidence_note": "Resumable API-Football league+season fixture backfill for Top-5 seasons 2017/18-2025/26. Referee is provider text with no stable referee ID; missing referee values remain UNKNOWN.",
        },
        "prematch_context_research": {
            "present": data["prematch_context"] is not None,
            "meta_present": prematch_context_meta is not None,
            "meta_valid": prematch_context_meta_valid,
            "rows": len(prematch_context),
            "valid_rows": len(prematch_context_valid),
            "invalid_rows": prematch_context_invalid,
            "unique_historical_match_ids": len(prematch_context_ids),
            "duplicate_historical_match_ids": prematch_context_duplicate_ids,
            "league_seasons": len(prematch_context_league_seasons),
            "expected_league_seasons": 45,
            "rows_with_kickoff_time": int(prematch_context_meta.get("rows_with_kickoff_time") or 0) if prematch_context_meta_valid else None,
            "rows_with_both_rest": int(prematch_context_meta.get("rows_with_both_rest") or 0) if prematch_context_meta_valid else None,
            "rows_with_both_pre_match_rank": int(prematch_context_meta.get("rows_with_both_pre_match_rank") or 0) if prematch_context_meta_valid else None,
            "rows_with_both_full_last5": int(prematch_context_meta.get("rows_with_both_full_last5") or 0) if prematch_context_meta_valid else None,
            "rows_with_both_full_last10": int(prematch_context_meta.get("rows_with_both_full_last10") or 0) if prematch_context_meta_valid else None,
            "same_day_results_excluded": bool(prematch_context_meta.get("same_day_results_excluded")) if prematch_context_meta_valid else None,
            "no_lookahead": bool(prematch_context_meta.get("no_lookahead")) if prematch_context_meta_valid else None,
            "provider_calls": int(prematch_context_meta.get("provider_calls") or 0) if prematch_context_meta_valid else None,
            "operational_betting_authority": False,
            "evidence_note": "Deterministic Football-Data Top-5 2017/18-2025/26 pre-match research projection. Features use strictly earlier calendar dates within league-season; same-day results are excluded and the layer has no probability/EV/eligibility/stake/Forward authority.",
        },
        "prematch_factor_research": {
            "profiles_present": data["prematch_factor_research"] is not None,
            "stability_present": data["prematch_factor_stability"] is not None,
            "meta_present": prematch_factor_meta is not None,
            "meta_valid": prematch_factor_meta_valid,
            "profile_rows": len(prematch_factor_research),
            "valid_profile_rows": len(prematch_factor_valid),
            "invalid_profile_rows": prematch_factor_invalid,
            "stability_rows": len(prematch_factor_stability),
            "valid_stability_rows": len(prematch_factor_stability_valid),
            "invalid_stability_rows": prematch_factor_stability_invalid,
            "factor_names": expected_factor_names,
            "closing_1x2_matches": int(prematch_factor_meta.get("closing_1x2_matches") or 0) if prematch_factor_meta_valid else None,
            "closing_total25_matches": int(prematch_factor_meta.get("closing_total25_matches") or 0) if prematch_factor_meta_valid else None,
            "market_probability_semantics": "Historical closing-market no-vig only; never PBK probability.",
            "operational_betting_authority": False,
            "evidence_note": "Descriptive factor buckets and season-stability counts from no-lookahead prematch context joined to historical outcomes/closing markets. Observed ROI/calibration is research evidence only and does not promote a factor into a model.",
        },
        "prematch_factor_walkforward": {
            "folds_present": data["prematch_walkforward"] is not None,
            "summary_present": data["prematch_walkforward_summary"] is not None,
            "meta_present": prematch_walkforward_meta is not None,
            "meta_valid": prematch_walkforward_meta_valid,
            "fold_rows": len(prematch_walkforward),
            "valid_fold_rows": len(prematch_walkforward_valid),
            "invalid_fold_rows": prematch_walkforward_invalid,
            "summary_rows": len(prematch_walkforward_summary),
            "valid_summary_rows": len(prematch_walkforward_summary_valid),
            "invalid_summary_rows": prematch_walkforward_summary_invalid,
            "sample_threshold_pass_folds": int(prematch_walkforward_meta.get("sample_threshold_pass_folds") or 0) if prematch_walkforward_meta_valid else None,
            "targets": list(prematch_walkforward_meta.get("targets") or []) if prematch_walkforward_meta_valid else [],
            "min_prior_seasons": 2,
            "min_train_market_matches": 100,
            "min_test_market_matches": 30,
            "market_probability_semantics": "Historical closing-market no-vig benchmark only; never PBK probability.",
            "operational_betting_authority": False,
            "promotes_factor": False,
            "evidence_note": "Walk-forward research uses only strictly earlier seasons to evaluate each later test season. Sample-qualified sign persistence is descriptive validation evidence only.",
        },
        "pbk14_historical_market_bridge": {
            "present": data["pbk14_market_bridge"] is not None,
            "source_meta_present": pbk14_market_source_meta is not None,
            "source_meta_valid": pbk14_market_source_meta_valid,
            "bridge_meta_present": pbk14_market_bridge_meta is not None,
            "bridge_meta_valid": pbk14_market_bridge_meta_valid,
            "rows": len(pbk14_market_bridge),
            "valid_rows": len(pbk14_market_bridge_valid),
            "invalid_rows": pbk14_market_bridge_invalid,
            "unique_historical_match_ids": len(pbk14_market_bridge_ids),
            "duplicate_historical_match_ids": pbk14_market_bridge_duplicate_ids,
            "mapped_auto": pbk14_market_bridge_counts["AUTO"],
            "mapped_high": pbk14_market_bridge_counts["HIGH"],
            "mapped_auto_high": len(pbk14_market_bridge_mapped),
            "review": pbk14_market_bridge_counts["REVIEW"],
            "unmapped": pbk14_market_bridge_counts["UNMAPPED"],
            "duplicate_mapped_api_fixture_ids": pbk14_market_bridge_duplicate_api_ids,
            "supported_leagues": 14,
            "unsupported_locked_pbk_leagues": 2,
            "unsupported_countries": ["Latvia","Lithuania"],
            "fuzzy_string_matching_used": False,
            "review_unmapped_excluded": True,
            "final_score_identity_only": True,
            "operational_betting_authority": False,
            "evidence_note": "Conservative historical identity bridge only. AUTO/HIGH can be joined downstream; REVIEW/UNMAPPED are excluded. Lithuania and Latvia have no Football-Data market source in this contour.",
        },
        "pbk14_international_window_market_join": {
            "present": data["pbk14_international_window_market_join"] is not None,
            "meta_present": pbk14_international_join_meta is not None,
            "meta_valid": pbk14_international_join_meta_valid,
            "rows": len(pbk14_international_join),
            "valid_rows": len(pbk14_international_join_valid),
            "invalid_rows": pbk14_international_join_invalid,
            "duplicate_historical_match_ids": pbk14_international_join_duplicate_hist_ids,
            "duplicate_api_fixture_ids": pbk14_international_join_duplicate_api_ids,
            "closing_1x2_matches": int(pbk14_international_join_meta.get("closing_1x2_matches") or 0) if pbk14_international_join_meta_valid else None,
            "closing_total25_matches": int(pbk14_international_join_meta.get("closing_total25_matches") or 0) if pbk14_international_join_meta_valid else None,
            "within_72h_before_rows": int(pbk14_international_join_meta.get("within_72h_before_rows") or 0) if pbk14_international_join_meta_valid else None,
            "within_96h_before_rows": int(pbk14_international_join_meta.get("within_96h_before_rows") or 0) if pbk14_international_join_meta_valid else None,
            "within_72h_after_rows": int(pbk14_international_join_meta.get("within_72h_after_rows") or 0) if pbk14_international_join_meta_valid else None,
            "within_96h_after_rows": int(pbk14_international_join_meta.get("within_96h_after_rows") or 0) if pbk14_international_join_meta_valid else None,
            "either_first_domestic_after_window_rows": int(pbk14_international_join_meta.get("either_first_domestic_after_window_rows") or 0) if pbk14_international_join_meta_valid else None,
            "player_level_international_status": pbk14_international_join_meta.get("player_level_international_status") if pbk14_international_join_meta_valid else None,
            "market_probability_semantics": "Historical closing odds are market benchmarks only; no PBK probability is created by this join.",
            "operational_betting_authority": False,
            "evidence_note": "AUTO/HIGH historical market rows joined to calendar-level international-window context. Calendar proximity never proves player duty; player call-up/travel/appearance remains UNVERIFIED.",
        },
        "pbk14_congestion_market_research": {
            "join_present": data["pbk14_congestion_market_join"] is not None,
            "join_meta_present": pbk14_congestion_join_meta is not None,
            "join_meta_valid": pbk14_congestion_join_meta_valid,
            "join_rows": len(pbk14_congestion_join),
            "valid_join_rows": len(pbk14_congestion_join_valid),
            "invalid_join_rows": pbk14_congestion_join_invalid,
            "duplicate_historical_match_ids": pbk14_congestion_join_duplicate_hist_ids,
            "duplicate_api_fixture_ids": pbk14_congestion_join_duplicate_api_ids,
            "profile_present": data["pbk14_congestion_market_profiles"] is not None,
            "stability_present": data["pbk14_congestion_market_stability"] is not None,
            "research_meta_present": pbk14_congestion_research_meta is not None,
            "research_meta_valid": pbk14_congestion_research_meta_valid,
            "profile_rows": len(pbk14_congestion_profiles),
            "valid_profile_rows": len(pbk14_congestion_profiles_valid),
            "invalid_profile_rows": pbk14_congestion_profiles_invalid,
            "stability_rows": len(pbk14_congestion_stability),
            "valid_stability_rows": len(pbk14_congestion_stability_valid),
            "invalid_stability_rows": pbk14_congestion_stability_invalid,
            "closing_1x2_matches": int(pbk14_congestion_research_meta.get("closing_1x2_matches") or 0) if pbk14_congestion_research_meta_valid else None,
            "closing_total25_matches": int(pbk14_congestion_research_meta.get("closing_total25_matches") or 0) if pbk14_congestion_research_meta_valid else None,
            "factor_names": sorted(expected_congestion_factors),
            "market_probability_semantics": "Historical closing-market no-vig benchmark only; never PBK probability.",
            "operational_betting_authority": False,
            "promotes_factor": False,
            "evidence_note": "Descriptive competition-load research over strict AUTO/HIGH PBK14 historical market joins. No factor is promoted here; walk-forward is a separate validation step.",
        },
        "pbk14_congestion_market_walkforward": {
            "folds_present": data["pbk14_congestion_market_walkforward"] is not None,
            "summary_present": data["pbk14_congestion_market_walkforward_summary"] is not None,
            "meta_present": pbk14_congestion_walkforward_meta is not None,
            "meta_valid": pbk14_congestion_walkforward_meta_valid,
            "fold_rows": len(pbk14_congestion_walkforward),
            "valid_fold_rows": len(pbk14_congestion_walkforward_valid),
            "invalid_fold_rows": pbk14_congestion_walkforward_invalid,
            "temporal_invalid_rows": pbk14_congestion_walkforward_temporal_invalid,
            "summary_rows": len(pbk14_congestion_walkforward_summary),
            "valid_summary_rows": len(pbk14_congestion_walkforward_summary_valid),
            "invalid_summary_rows": pbk14_congestion_walkforward_summary_invalid,
            "sample_threshold_pass_folds": int(pbk14_congestion_walkforward_meta.get("sample_threshold_pass_folds") or 0) if pbk14_congestion_walkforward_meta_valid else None,
            "min_prior_seasons": 2,
            "min_train_market_matches": 100,
            "min_test_market_matches": 30,
            "market_probability_semantics": "Historical closing-market no-vig benchmark only; never PBK probability.",
            "operational_betting_authority": False,
            "promotes_factor": False,
            "evidence_note": "Each test season is evaluated using only earlier seasons. Persistence remains research evidence and cannot promote a congestion factor.",
        },
        "pbk16_competition_history": {
            "catalog_present": data["pbk16_competition_catalog"] is not None,
            "fixture_archive_present": data["pbk16_competition_fixtures"] is not None,
            "state_present": data["pbk16_competition_state"] is not None,
            "meta_present": pbk16_competition_meta is not None,
            "meta_valid": pbk16_competition_meta_valid,
            "catalog_rows": len(pbk16_catalog),
            "valid_catalog_rows": len(pbk16_catalog_valid),
            "invalid_catalog_rows": pbk16_catalog_invalid,
            "required_unresolved_competitions": len(pbk16_required_unresolved),
            "optional_unresolved_competitions": len(pbk16_optional_unresolved),
            "resolved_domestic_league_catalog_ids": len(pbk16_resolved_domestic_league_catalog),
            "fixture_rows": len(pbk16_fixtures),
            "valid_fixture_rows": len(pbk16_fixture_valid),
            "invalid_fixture_rows": pbk16_fixture_invalid,
            "duplicate_fixture_ids": pbk16_fixture_duplicate_ids,
            "domestic_anchor_rows": len(pbk16_domestic_fixture_rows),
            "domestic_anchor_league_ids": len(pbk16_domestic_anchor_league_ids),
            "state_rows": len(pbk16_state),
            "valid_state_rows": len(pbk16_state_valid),
            "invalid_state_rows": pbk16_state_invalid,
            "captured_fixture_cells": pbk16_state_captured,
            "unavailable_provider_season_cells": pbk16_state_unavailable,
            "pending_fixture_cells": pbk16_state_pending,
            "error_fixture_cells": pbk16_state_errors,
            "operational_betting_authority": False,
            "evidence_note": "Historical PBK16 domestic-league/cup + UEFA provider archive. Provider-unavailable seasons and unresolved required competitions remain explicit gaps; no betting/model authority.",
        },
        "pbk16_competition_congestion": {
            "present": data["pbk16_competition_congestion"] is not None,
            "meta_present": pbk16_congestion_meta is not None,
            "meta_valid": pbk16_congestion_meta_valid,
            "rows": len(pbk16_congestion),
            "valid_rows": len(pbk16_congestion_valid),
            "invalid_rows": pbk16_congestion_invalid,
            "unique_domestic_fixture_ids": len(pbk16_congestion_ids),
            "duplicate_domestic_fixture_ids": pbk16_congestion_duplicate_ids,
            "strictly_prior_fixture_evidence_only": bool(
                pbk16_congestion_meta.get("strictly_prior_fixture_evidence_only")
            ) if pbk16_congestion_meta_valid else None,
            "future_schedule_used": pbk16_congestion_meta.get("future_schedule_used") if pbk16_congestion_meta_valid else None,
            "no_lookahead": pbk16_congestion_meta.get("no_lookahead") if pbk16_congestion_meta_valid else None,
            "rows_either_prev_nonleague_72h": int(pbk16_congestion_meta.get("rows_either_prev_nonleague_72h") or 0) if pbk16_congestion_meta_valid else None,
            "rows_either_prev_uefa_72h": int(pbk16_congestion_meta.get("rows_either_prev_uefa_72h") or 0) if pbk16_congestion_meta_valid else None,
            "rows_either_prev_cup_72h": int(pbk16_congestion_meta.get("rows_either_prev_cup_72h") or 0) if pbk16_congestion_meta_valid else None,
            "rows_either_previous_nonleague_was_thursday": int(pbk16_congestion_meta.get("rows_either_previous_nonleague_was_thursday") or 0) if pbk16_congestion_meta_valid else None,
            "operational_betting_authority": False,
            "evidence_note": "One deterministic row per captured PBK16 domestic fixture; only strictly prior played cup/UEFA evidence can contribute. Future scheduled fixtures are excluded.",
        },
        "pbk16_international_window_context": {
            "present": data["pbk16_international_window_context"] is not None,
            "meta_present": pbk16_international_meta is not None,
            "meta_valid": pbk16_international_meta_valid,
            "rows": len(pbk16_international),
            "valid_rows": len(pbk16_international_valid),
            "invalid_rows": pbk16_international_invalid,
            "unique_domestic_fixture_ids": len(pbk16_international_ids),
            "duplicate_domestic_fixture_ids": pbk16_international_duplicate_ids,
            "calendar_windows": int(pbk16_international_meta.get("calendar_windows") or 0) if pbk16_international_meta_valid else None,
            "calendar_sources": int(pbk16_international_meta.get("calendar_sources") or 0) if pbk16_international_meta_valid else None,
            "window_reference_contract": pbk16_international_meta.get("window_reference_contract") if pbk16_international_meta_valid else None,
            "within_72h_before_rows": int(pbk16_international_meta.get("within_72h_before_rows") or 0) if pbk16_international_meta_valid else None,
            "within_96h_before_rows": int(pbk16_international_meta.get("within_96h_before_rows") or 0) if pbk16_international_meta_valid else None,
            "within_72h_after_rows": int(pbk16_international_meta.get("within_72h_after_rows") or 0) if pbk16_international_meta_valid else None,
            "within_96h_after_rows": int(pbk16_international_meta.get("within_96h_after_rows") or 0) if pbk16_international_meta_valid else None,
            "either_first_domestic_after_window_rows": int(pbk16_international_meta.get("either_first_domestic_after_window_rows") or 0) if pbk16_international_meta_valid else None,
            "player_level_international_status": pbk16_international_meta.get("player_level_international_status") if pbk16_international_meta_valid else None,
            "no_lookahead": pbk16_international_meta.get("no_lookahead") if pbk16_international_meta_valid else None,
            "operational_betting_authority": False,
            "evidence_note": "Calendar-level international-window proximity only. It does not infer any player call-up, travel, appearance, minutes or return timing; those remain UNVERIFIED without direct historical evidence.",
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
    profiles = report["player_profiles"]
    p = report["players"]
    advanced = report["advanced_metrics"]
    c = report["context"]
    identities = report["transfer_identity"]
    transfers = report["transfer_history"]
    events = report["match_events"]
    norm = report["normalized_context_archives"]
    referee = report["referee_research"]
    referee_top5 = report["referee_top5_backfill"]
    prematch = report["prematch_context_research"]
    prematch_factor = report["prematch_factor_research"]
    prematch_walkforward = report["prematch_factor_walkforward"]
    pbk14_market = report["pbk14_historical_market_bridge"]
    pbk14_international_market = report["pbk14_international_window_market_join"]
    pbk14_congestion_market = report["pbk14_congestion_market_research"]
    pbk14_congestion_wf = report["pbk14_congestion_market_walkforward"]
    pbk16_history = report["pbk16_competition_history"]
    pbk16_congestion = report["pbk16_competition_congestion"]
    pbk16_international = report["pbk16_international_window_context"]
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
        f"- Player profile evidence: {profiles['valid_rows']} rows ({profiles['team_source_rows']} team-source + {profiles['residual_player_id_source_rows']} residual-ID) / {profiles['unique_players']} players / {profiles['unique_teams']} teams; current-roster coverage {profiles['current_roster_player_coverage_pct'] if profiles['current_roster_player_coverage_pct'] is not None else '—'}%; identity-ready {profiles['identity_ready_unique_players']} players ({profiles['identity_ready_current_roster_coverage_pct'] if profiles['identity_ready_current_roster_coverage_pct'] is not None else '—'}%).",
        f"- Roster history: {r['history_teams']} команд / {r['history_team_snapshots']} team-snapshots / {r['history_rows']} строк.",
        f"- Membership intervals: {r['membership_intervals']} (open {r['open_latest_intervals']}, closed-by-observed-absence {r['closed_by_observed_absence_intervals']}).",
        f"- Verified PBK↔Transfermarkt identities: {identities['valid_rows']} rows / {identities['unique_pbk_players']} PBK players; invalid {identities['invalid_rows']}.",
        f"- Verified historical transfers: {transfers['valid_rows']} rows / {transfers['unique_pbk_players']} PBK players; dates {transfers['earliest_transfer_date'] or '—'} → {transfers['latest_transfer_date'] or '—'}; invalid {transfers['invalid_identity_rows']}.",
        f"- EPL referee research: {referee['unique_referees']} referees / {referee['valid_team_split_rows']} referee×team pairs / {referee['source_matches'] if referee['source_matches'] is not None else '—'} source matches; scope EPL_ONLY; penalties unavailable.",
        f"- Top-5 API-Football referee backfill: {referee_top5['captured_league_seasons']} / {referee_top5['expected_league_seasons']} league-seasons; {referee_top5['valid_fixture_rows']} fixture rows; referee coverage {referee_top5['referee_coverage_pct'] if referee_top5['referee_coverage_pct'] is not None else '—'}%; profiles {referee_top5['valid_profile_rows']}; referee×team pairs {referee_top5['valid_team_split_rows']}.",
        f"- Top-5 pre-match research context: {prematch['valid_rows']} valid rows / {prematch['unique_historical_match_ids']} unique matches / {prematch['league_seasons']} of {prematch['expected_league_seasons']} league-seasons; no-lookahead {prematch['no_lookahead']}.",
        f"- Pre-match factor research: {prematch_factor['valid_profile_rows']} profile rows / {prematch_factor['valid_stability_rows']} stability rows; closing 1X2 matches {prematch_factor['closing_1x2_matches'] if prematch_factor['closing_1x2_matches'] is not None else '—'}; closing O/U2.5 matches {prematch_factor['closing_total25_matches'] if prematch_factor['closing_total25_matches'] is not None else '—'}.",
        f"- Pre-match walk-forward research: {prematch_walkforward['valid_fold_rows']} folds / {prematch_walkforward['valid_summary_rows']} summaries; sample-qualified folds {prematch_walkforward['sample_threshold_pass_folds'] if prematch_walkforward['sample_threshold_pass_folds'] is not None else '—'}; promotes factor {prematch_walkforward['promotes_factor']}.",
        f"- Match context: {c['unique_fixtures']} fixtures; official XI {c['fixtures_with_official_lineup_snapshot']}; injury evidence {c['fixtures_with_injury_evidence']}.",
        f"- PBK14 historical market bridge: {pbk14_market['mapped_auto_high']} AUTO/HIGH of {pbk14_market['valid_rows']} valid source rows; AUTO {pbk14_market['mapped_auto']}, HIGH {pbk14_market['mapped_high']}, REVIEW {pbk14_market['review']}, UNMAPPED {pbk14_market['unmapped']}; fuzzy matching {pbk14_market['fuzzy_string_matching_used']}; source coverage 14 / 16 locked leagues.",
        f"- PBK14 international-window × market join: {pbk14_international_market['valid_rows']} valid rows; closing 1X2 {pbk14_international_market['closing_1x2_matches'] if pbk14_international_market['closing_1x2_matches'] is not None else '—'}; closing O/U2.5 {pbk14_international_market['closing_total25_matches'] if pbk14_international_market['closing_total25_matches'] is not None else '—'}; <=72h before {pbk14_international_market['within_72h_before_rows'] if pbk14_international_market['within_72h_before_rows'] is not None else '—'}; <=72h after {pbk14_international_market['within_72h_after_rows'] if pbk14_international_market['within_72h_after_rows'] is not None else '—'}; player-level {pbk14_international_market['player_level_international_status'] or '—'}.",
        f"- PBK14 congestion × market research: join {pbk14_congestion_market['valid_join_rows']} rows; descriptive profiles {pbk14_congestion_market['valid_profile_rows']}; stability rows {pbk14_congestion_market['valid_stability_rows']}; closing 1X2 {pbk14_congestion_market['closing_1x2_matches'] if pbk14_congestion_market['closing_1x2_matches'] is not None else '—'}; closing O/U2.5 {pbk14_congestion_market['closing_total25_matches'] if pbk14_congestion_market['closing_total25_matches'] is not None else '—'}; promotes factor {pbk14_congestion_market['promotes_factor']}.",
        f"- PBK14 congestion walk-forward: {pbk14_congestion_wf['valid_fold_rows']} valid folds / {pbk14_congestion_wf['valid_summary_rows']} summaries; qualified folds {pbk14_congestion_wf['sample_threshold_pass_folds'] if pbk14_congestion_wf['sample_threshold_pass_folds'] is not None else '—'}; temporal invalid {pbk14_congestion_wf['temporal_invalid_rows']}; promotes factor {pbk14_congestion_wf['promotes_factor']}.",
        f"- PBK16 all-competition history: catalog {pbk16_history['valid_catalog_rows']} valid rows; required unresolved {pbk16_history['required_unresolved_competitions']}; fixture archive {pbk16_history['valid_fixture_rows']} valid rows; domestic anchors {pbk16_history['domestic_anchor_league_ids']} / 16 leagues; captured cells {pbk16_history['captured_fixture_cells']}, provider-unavailable cells {pbk16_history['unavailable_provider_season_cells']}, pending {pbk16_history['pending_fixture_cells']}, errors {pbk16_history['error_fixture_cells']}.",
        f"- PBK16 cup/UEFA congestion: {pbk16_congestion['valid_rows']} valid rows / {pbk16_congestion['unique_domestic_fixture_ids']} domestic fixtures; no-lookahead {pbk16_congestion['no_lookahead']}; future schedule used {pbk16_congestion['future_schedule_used']}; prior UEFA <=72h {pbk16_congestion['rows_either_prev_uefa_72h'] if pbk16_congestion['rows_either_prev_uefa_72h'] is not None else '—'}, prior cup <=72h {pbk16_congestion['rows_either_prev_cup_72h'] if pbk16_congestion['rows_either_prev_cup_72h'] is not None else '—'}.",
        f"- PBK16 international windows: {pbk16_international['valid_rows']} valid rows / {pbk16_international['unique_domestic_fixture_ids']} domestic fixtures; calendar windows {pbk16_international['calendar_windows'] if pbk16_international['calendar_windows'] is not None else '—'}; <=72h before {pbk16_international['within_72h_before_rows'] if pbk16_international['within_72h_before_rows'] is not None else '—'}, <=72h after {pbk16_international['within_72h_after_rows'] if pbk16_international['within_72h_after_rows'] is not None else '—'}; player-level {pbk16_international['player_level_international_status'] or '—'}; no-lookahead {pbk16_international['no_lookahead']}.",
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
        "player_profile_identity_ready_players": report["player_profiles"]["identity_ready_unique_players"],
        "player_profile_roster_coverage_pct": report["player_profiles"]["current_roster_player_coverage_pct"],
        "raw_archive_status": report["raw_provider_archive"]["status"],
        "verified_transfer_identity_rows": report["transfer_identity"]["valid_rows"],
        "verified_transfer_rows": report["transfer_history"]["valid_rows"],
        "team_xg_complete_fixtures": report["advanced_metrics"]["team_xg_complete_fixture_count"],
        "player_xg_xa_source_status": report["advanced_metrics"]["player_xg_xa_source_status"],
        "referee_research_unique_referees": report["referee_research"]["unique_referees"],
        "referee_research_team_pairs": report["referee_research"]["valid_team_split_rows"],
        "top5_referee_backfill_league_seasons": report["referee_top5_backfill"]["captured_league_seasons"],
        "top5_referee_backfill_fixture_rows": report["referee_top5_backfill"]["valid_fixture_rows"],
        "top5_referee_backfill_coverage_pct": report["referee_top5_backfill"]["referee_coverage_pct"],
        "prematch_context_rows": report["prematch_context_research"]["valid_rows"],
        "prematch_context_league_seasons": report["prematch_context_research"]["league_seasons"],
        "prematch_context_no_lookahead": report["prematch_context_research"]["no_lookahead"],
        "prematch_factor_profile_rows": report["prematch_factor_research"]["valid_profile_rows"],
        "prematch_factor_stability_rows": report["prematch_factor_research"]["valid_stability_rows"],
        "prematch_walkforward_fold_rows": report["prematch_factor_walkforward"]["valid_fold_rows"],
        "prematch_walkforward_summary_rows": report["prematch_factor_walkforward"]["valid_summary_rows"],
        "prematch_walkforward_sample_qualified_folds": report["prematch_factor_walkforward"]["sample_threshold_pass_folds"],
        "pbk14_market_bridge_rows": report["pbk14_historical_market_bridge"]["valid_rows"],
        "pbk14_congestion_market_join_rows": report["pbk14_congestion_market_research"]["valid_join_rows"],
        "pbk14_congestion_market_profile_rows": report["pbk14_congestion_market_research"]["valid_profile_rows"],
        "pbk14_congestion_market_stability_rows": report["pbk14_congestion_market_research"]["valid_stability_rows"],
        "pbk14_congestion_walkforward_fold_rows": report["pbk14_congestion_market_walkforward"]["valid_fold_rows"],
        "pbk14_congestion_walkforward_summary_rows": report["pbk14_congestion_market_walkforward"]["valid_summary_rows"],
        "pbk14_congestion_walkforward_qualified_folds": report["pbk14_congestion_market_walkforward"]["sample_threshold_pass_folds"],
        "pbk14_market_bridge_mapped_auto_high": report["pbk14_historical_market_bridge"]["mapped_auto_high"],
        "pbk14_international_window_market_join_rows": report["pbk14_international_window_market_join"]["valid_rows"],
        "pbk14_market_bridge_review": report["pbk14_historical_market_bridge"]["review"],
        "pbk14_market_bridge_unmapped": report["pbk14_historical_market_bridge"]["unmapped"],
        "pbk16_competition_fixture_rows": report["pbk16_competition_history"]["valid_fixture_rows"],
        "pbk16_competition_domestic_anchor_leagues": report["pbk16_competition_history"]["domestic_anchor_league_ids"],
        "pbk16_competition_required_unresolved": report["pbk16_competition_history"]["required_unresolved_competitions"],
        "pbk16_competition_congestion_rows": report["pbk16_competition_congestion"]["valid_rows"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
