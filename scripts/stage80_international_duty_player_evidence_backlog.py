#!/usr/bin/env python3
"""Stage80 — deterministic player-evidence backlog for international duty.

Consumes the completed national-team fixture archive and queues only finished
fixtures that:
1) belong to an allowlisted player-evidence tier, and
2) fall INSIDE one of the 39 configured UEFA-relevant fixed international
   A-match windows from 2017-2025.

This deliberately excludes final tournaments and other out-of-window national
fixtures from the international-break player-duty contour.

Capture endpoint by evidence tier:
- DIRECT_MINUTES -> /fixtures/players
- DIRECT_MATCHDAY_SQUAD -> /fixtures/lineups

This file creates queue state only. It makes zero provider calls and does not
infer call-up, travel, appearance, starter/substitute status, minutes, or return.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import stage80_pbk16_international_window_context as iw

OPS = Path(os.getenv("OPS_DIR", "ops"))
FIXTURES = OPS / "international_team_fixture_history.csv"
FIXTURE_META = OPS / "stage80_international_duty_fixture_backfill_last_run.json"
CONFIG = Path("config/stage80_fifa_uefa_windows_2017_2025.json")
BACKLOG = OPS / "international_duty_player_evidence_backlog.csv"
META = OPS / "stage80_international_duty_player_evidence_backlog_last_run.json"

VERSION = "PBK_STAGE80_INTERNATIONAL_DUTY_PLAYER_EVIDENCE_BACKLOG_V1"
FINAL_STATUSES = {"FT", "AET", "PEN"}
ELIGIBLE_TIERS = {"DIRECT_MINUTES", "DIRECT_MATCHDAY_SQUAD"}

FIELDS = [
    "fixture_id","provider_league_id","competition_name","candidate_family",
    "season","round","kickoff_utc","source_status",
    "home_team_id","home_team","away_team_id","away_team",
    "evidence_tier","capture_endpoint","capture_priority",
    "window_id","window_start_utc","window_end_utc","window_max_matches",
    "queue_reason","first_queued_at_utc","last_seen_at_utc",
    "backlog_status","captured_at_utc","attempt_count","last_attempt_at_utc",
    "last_attempt_result","last_error",
    "callup_inference_allowed","nationality_inference_allowed",
    "travel_inference_allowed","appearance_inference_allowed",
    "historical_backfill_only","research_only","operational_betting_authority",
    "creates_signal","probability_mutation","eligibility_mutation",
    "stake_changes","forward_journal_mutation",
]

PRESERVABLE_STATUSES = {"PENDING", "CAPTURED", "NO_DATA", "ERROR"}


def iso_now(now=None):
    now = now or datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def btrue(value):
    return str(value or "").strip().lower() in {"1","true","yes","y"}


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z","+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {"_invalid_json": True}


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def window_for_kickoff(kickoff, windows):
    matches = [w for w in windows if w["start"] <= kickoff <= w["end"]]
    if len(matches) > 1:
        raise ValueError(f"overlapping configured windows at {kickoff.isoformat()}")
    return matches[0] if matches else None


def valid_source_fixture(row):
    return bool(
        sval(row, "fixture_id")
        and sval(row, "provider_league_id")
        and sval(row, "season")
        and parse_dt(row.get("kickoff_utc")) is not None
        and sval(row, "home_team_id")
        and sval(row, "away_team_id")
        and sval(row, "status") in FINAL_STATUSES
        and sval(row, "evidence_tier") in ELIGIBLE_TIERS
        and sval(row, "player_evidence_backfill_eligible") == "true"
        and sval(row, "historical_callup_evidence_possible") == "false"
        and sval(row, "nationality_inference_allowed") == "false"
        and sval(row, "historical_backfill_only") == "true"
        and sval(row, "research_only") == "true"
        and sval(row, "operational_betting_authority") == "false"
        and sval(row, "creates_signal") == "false"
        and sval(row, "probability_mutation") == "false"
        and sval(row, "eligibility_mutation") == "false"
        and sval(row, "stake_changes") == "false"
        and sval(row, "forward_journal_mutation") == "false"
    )


def endpoint_for_tier(tier):
    if tier == "DIRECT_MINUTES":
        return "/fixtures/players"
    if tier == "DIRECT_MATCHDAY_SQUAD":
        return "/fixtures/lineups"
    raise ValueError(f"unsupported evidence tier: {tier}")


def priority_for_tier(tier):
    if tier == "DIRECT_MINUTES":
        return 1
    if tier == "DIRECT_MATCHDAY_SQUAD":
        return 2
    raise ValueError(f"unsupported evidence tier: {tier}")


def build_backlog(source_rows, existing_rows, windows, now=None):
    now_iso = iso_now(now)
    existing = {
        sval(row, "fixture_id"): dict(row)
        for row in existing_rows
        if sval(row, "fixture_id")
    }

    source_ids = []
    invalid_source_rows = 0
    source_finished_rows = 0
    source_finished_eligible_rows = 0
    outside_window_finished_eligible_rows = 0
    queued = []

    for row in source_rows:
        fixture_id = sval(row, "fixture_id")
        if fixture_id:
            source_ids.append(fixture_id)
        if sval(row, "status") in FINAL_STATUSES:
            source_finished_rows += 1

        if not valid_source_fixture(row):
            if (
                sval(row, "status") in FINAL_STATUSES
                and sval(row, "evidence_tier") in ELIGIBLE_TIERS
                and sval(row, "player_evidence_backfill_eligible") == "true"
            ):
                invalid_source_rows += 1
            continue

        source_finished_eligible_rows += 1
        kickoff = parse_dt(row.get("kickoff_utc"))
        window = window_for_kickoff(kickoff, windows)
        if window is None:
            outside_window_finished_eligible_rows += 1
            continue

        old = existing.get(fixture_id, {})
        status = sval(old, "backlog_status")
        if status not in PRESERVABLE_STATUSES:
            status = "PENDING"

        first_queued = sval(old, "first_queued_at_utc") or now_iso
        capture_endpoint = endpoint_for_tier(sval(row, "evidence_tier"))

        queued.append({
            "fixture_id": fixture_id,
            "provider_league_id": sval(row, "provider_league_id"),
            "competition_name": sval(row, "competition_name"),
            "candidate_family": sval(row, "candidate_family"),
            "season": sval(row, "season"),
            "round": sval(row, "round"),
            "kickoff_utc": sval(row, "kickoff_utc"),
            "source_status": sval(row, "status"),
            "home_team_id": sval(row, "home_team_id"),
            "home_team": sval(row, "home_team"),
            "away_team_id": sval(row, "away_team_id"),
            "away_team": sval(row, "away_team"),
            "evidence_tier": sval(row, "evidence_tier"),
            "capture_endpoint": capture_endpoint,
            "capture_priority": str(priority_for_tier(sval(row, "evidence_tier"))),
            "window_id": window["window_id"],
            "window_start_utc": iw.iso(window["start"]),
            "window_end_utc": iw.iso(window["end"]),
            "window_max_matches": str(window["max_matches"]),
            "queue_reason": "FINISHED_ALLOWLISTED_FIXTURE_INSIDE_FIXED_INTL_WINDOW",
            "first_queued_at_utc": first_queued,
            "last_seen_at_utc": now_iso,
            "backlog_status": status,
            "captured_at_utc": sval(old, "captured_at_utc"),
            "attempt_count": sval(old, "attempt_count") or "0",
            "last_attempt_at_utc": sval(old, "last_attempt_at_utc"),
            "last_attempt_result": sval(old, "last_attempt_result"),
            "last_error": sval(old, "last_error"),
            "callup_inference_allowed": "false",
            "nationality_inference_allowed": "false",
            "travel_inference_allowed": "false",
            "appearance_inference_allowed": "false",
            "historical_backfill_only": "true",
            "research_only": "true",
            "operational_betting_authority": "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })

    duplicate_source_fixture_ids = len(source_ids) - len(set(source_ids))
    if duplicate_source_fixture_ids:
        raise ValueError(f"duplicate source fixture ids: {duplicate_source_fixture_ids}")

    queued.sort(key=lambda row: (
        int(row["capture_priority"]),
        row["kickoff_utc"],
        row["fixture_id"],
    ))

    queued_ids = [row["fixture_id"] for row in queued]
    duplicate_backlog_fixture_ids = len(queued_ids) - len(set(queued_ids))
    if duplicate_backlog_fixture_ids:
        raise ValueError(f"duplicate backlog fixture ids: {duplicate_backlog_fixture_ids}")

    diag = {
        "source_fixture_rows": len(source_rows),
        "source_finished_rows": source_finished_rows,
        "source_finished_player_evidence_eligible_rows": source_finished_eligible_rows,
        "outside_window_finished_player_evidence_eligible_rows": outside_window_finished_eligible_rows,
        "backlog_rows": len(queued),
        "duplicate_source_fixture_ids": duplicate_source_fixture_ids,
        "duplicate_backlog_fixture_ids": duplicate_backlog_fixture_ids,
        "invalid_source_rows": invalid_source_rows,
    }
    return queued, diag


def validate_fixture_meta(meta, source_rows):
    return bool(
        meta
        and not meta.get("_invalid_json")
        and meta.get("version") == "PBK_STAGE80_INTERNATIONAL_DUTY_FIXTURE_BACKFILL_V1"
        and meta.get("status") == "OK"
        and int(meta.get("allowlist_rows") or 0) == 80
        and int(meta.get("state_rows") or 0) == 80
        and int(meta.get("captured_cells") or 0) == 80
        and int(meta.get("pending_cells") or 0) == 0
        and int(meta.get("error_cells") or 0) == 0
        and int(meta.get("fixture_archive_rows") or 0) == len(source_rows)
        and int(meta.get("unique_fixture_ids") or 0) == len(source_rows)
        and int(meta.get("duplicate_fixture_ids") or 0) == 0
        and int(meta.get("invalid_archive_rows") or 0) == 0
        and meta.get("historical_callup_evidence_possible") is False
        and meta.get("nationality_inference_allowed") is False
        and meta.get("player_appearance_or_minutes_inferred") is False
        and meta.get("provider_fixture_history_only") is True
        and meta.get("research_only") is True
        and meta.get("operational_betting_authority") is False
    )


def run(
    fixtures_path=FIXTURES,
    fixture_meta_path=FIXTURE_META,
    config_path=CONFIG,
    backlog_path=BACKLOG,
    meta_path=META,
    now=None,
):
    source_rows = read_csv(fixtures_path)
    fixture_meta = read_json(fixture_meta_path)
    if not validate_fixture_meta(fixture_meta, source_rows):
        raise ValueError("international-duty fixture archive/meta contract is not ready")

    cfg, windows = iw.load_config(config_path)
    existing_rows = read_csv(backlog_path)
    backlog, diag = build_backlog(source_rows, existing_rows, windows, now=now)

    statuses = Counter(sval(row, "backlog_status") for row in backlog)
    tiers = Counter(sval(row, "evidence_tier") for row in backlog)
    endpoints = Counter(sval(row, "capture_endpoint") for row in backlog)
    windows_used = Counter(sval(row, "window_id") for row in backlog)

    invalid_backlog_rows = sum(
        not (
            sval(row, "fixture_id")
            and sval(row, "capture_endpoint") in {"/fixtures/players", "/fixtures/lineups"}
            and sval(row, "evidence_tier") in ELIGIBLE_TIERS
            and sval(row, "window_id")
            and sval(row, "source_status") in FINAL_STATUSES
            and sval(row, "callup_inference_allowed") == "false"
            and sval(row, "nationality_inference_allowed") == "false"
            and sval(row, "travel_inference_allowed") == "false"
            and sval(row, "appearance_inference_allowed") == "false"
            and sval(row, "research_only") == "true"
            and sval(row, "operational_betting_authority") == "false"
            and sval(row, "creates_signal") == "false"
        )
        for row in backlog
    )

    status = "OK" if (
        diag["duplicate_source_fixture_ids"] == 0
        and diag["duplicate_backlog_fixture_ids"] == 0
        and diag["invalid_source_rows"] == 0
        and invalid_backlog_rows == 0
        and len(backlog) > 0
        and all(row["queue_reason"] == "FINISHED_ALLOWLISTED_FIXTURE_INSIDE_FIXED_INTL_WINDOW" for row in backlog)
    ) else "ATTENTION"

    meta = {
        "version": VERSION,
        "generated_at_utc": iso_now(now),
        "status": status,
        **diag,
        "invalid_backlog_rows": invalid_backlog_rows,
        "configured_windows": len(windows),
        "configured_window_version": cfg.get("version"),
        "backlog_window_count": len(windows_used),
        "backlog_window_counts": dict(sorted(windows_used.items())),
        "evidence_tier_counts": dict(sorted(tiers.items())),
        "capture_endpoint_counts": dict(sorted(endpoints.items())),
        "backlog_status_counts": dict(sorted(statuses.items())),
        "final_tournaments_included": False,
        "outside_fixed_window_fixtures_queued": False,
        "callup_inference_allowed": False,
        "nationality_inference_allowed": False,
        "travel_inference_allowed": False,
        "appearance_inference_allowed": False,
        "player_minutes_claimed_before_capture": False,
        "provider_calls": 0,
        "historical_backfill_only": True,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "next_stage": (
            "Capture direct fixture-player evidence for backlog rows. "
            "DIRECT_MINUTES uses /fixtures/players; DIRECT_MATCHDAY_SQUAD uses /fixtures/lineups."
        ),
    }
    write_csv(backlog_path, backlog)
    write_json(meta_path, meta)
    return meta


def main():
    print(json.dumps(run(), ensure_ascii=False))


if __name__ == "__main__":
    main()
