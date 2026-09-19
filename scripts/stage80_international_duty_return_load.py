#!/usr/bin/env python3
"""Stage80 — direct-evidence international-duty workload and club-return projection.

Input authority:
- direct international player evidence only;
- bounded Transfermarkt club -> PBK16 team identity only;
- durable PBK16 all-competition archive for the next actually played domestic
  league fixture.

No nationality/call-up/travel inference. No current-club shortcut. No provider
calls. The projection is research-only and does not create model authority.
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
EVIDENCE = OPS / "international_duty_player_evidence.csv"
EVIDENCE_META = OPS / "stage80_international_duty_player_evidence_capture_last_run.json"
CLUB_IDENTITY = OPS / "international_duty_player_pbk16_club_identity.csv"
CLUB_META = OPS / "stage80_international_duty_pbk16_club_identity_last_run.json"
ARCHIVE = OPS / "pbk16_all_competition_fixture_history.csv"
ARCHIVE_META = OPS / "stage80_pbk16_competition_backfill_last_run.json"
OUTPUT = OPS / "international_duty_player_return_load.csv"
META = OPS / "stage80_international_duty_return_load_last_run.json"

VERSION = "PBK_STAGE80_INTERNATIONAL_DUTY_RETURN_LOAD_V1_DIRECT_EVIDENCE"
EVIDENCE_VERSION = "PBK_STAGE80_INTERNATIONAL_DUTY_PLAYER_EVIDENCE_CAPTURE_V2_STRICT_ROLE_SEMANTICS"
CLUB_VERSION = "PBK_STAGE80_INTERNATIONAL_DUTY_PBK16_CLUB_IDENTITY_V1_EXACT_ALIAS_UNIQUE"
ARCHIVE_VERSION = "PBK_STAGE80_PBK16_ALL_COMPETITION_BACKFILL_V1"
FINAL = {"FT", "AET", "PEN"}
MAX_RETURN_HORIZON_HOURS = 14 * 24

FIELDS = [
    "international_fixture_id","international_kickoff_utc","window_id",
    "national_team_id","national_team_name","player_id","player_name",
    "pbk16_team_id","pbk16_team_name","pbk16_provider_league_id",
    "appearance_confirmed","minutes_confirmed","confirmed_minutes",
    "window_direct_evidence_fixture_count_through_event",
    "window_confirmed_appearances_through_event",
    "window_minutes_confirmed_fixture_count_through_event",
    "window_confirmed_minutes_through_event",
    "next_domestic_fixture_id","next_domestic_kickoff_utc",
    "next_domestic_home_team_id","next_domestic_home_team",
    "next_domestic_away_team_id","next_domestic_away_team",
    "club_side","opponent_team_id","opponent_team",
    "hours_to_next_domestic_fixture","days_to_next_domestic_fixture",
    "return_within_72h","return_within_96h","return_within_7d",
    "return_fixture_status","return_fixture_played_only",
    "formal_callup_inferred","travel_inferred","current_club_used",
    "fuzzy_matching_used","provider_calls","research_only",
    "operational_betting_authority","creates_signal","probability_mutation",
    "eligibility_mutation","stake_changes","forward_journal_mutation",
]


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"_invalid_json": True}


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def bool_true(row, key):
    return sval(row, key).lower() == "true"


def as_int(value):
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def evidence_key(row):
    return (sval(row, "fixture_id"), sval(row, "player_id"))


def build_domestic_team_index(archive_rows):
    by_team = defaultdict(list)
    invalid = 0
    for row in archive_rows:
        if sval(row, "competition_role") != "DOMESTIC_LEAGUE":
            continue
        if sval(row, "status") not in FINAL:
            continue
        kickoff = parse_dt(row.get("kickoff_utc"))
        fixture_id = sval(row, "fixture_id")
        home_id = sval(row, "home_team_id")
        away_id = sval(row, "away_team_id")
        if not kickoff or not fixture_id or not home_id or not away_id:
            invalid += 1
            continue
        by_team[home_id].append((kickoff, row))
        by_team[away_id].append((kickoff, row))
    for team_id in by_team:
        by_team[team_id].sort(key=lambda item: (item[0], sval(item[1], "fixture_id")))
    return by_team, invalid


def next_played_domestic(team_rows, after_dt, max_horizon_hours=MAX_RETURN_HORIZON_HOURS):
    horizon = after_dt + timedelta(hours=max_horizon_hours)
    for kickoff, row in team_rows:
        if kickoff <= after_dt:
            continue
        if kickoff > horizon:
            return None, None, "OUTSIDE_RETURN_HORIZON"
        return kickoff, row, "FOUND"
    return None, None, "NO_LATER_FIXTURE"


def build(evidence_rows, club_rows, archive_rows):
    evidence = {}
    grouped = defaultdict(list)
    invalid_evidence = 0
    for row in evidence_rows:
        key = evidence_key(row)
        kickoff = parse_dt(row.get("kickoff_utc"))
        window_id = sval(row, "window_id")
        if not all(key) or not kickoff or not window_id:
            invalid_evidence += 1
            continue
        evidence[key] = row
        grouped[(key[1], window_id)].append((kickoff, row))
    for key in grouped:
        grouped[key].sort(key=lambda item: (item[0], sval(item[1], "fixture_id")))

    domestic, invalid_domestic = build_domestic_team_index(archive_rows)
    output = []
    missing_evidence = 0
    missing_return = 0
    return_beyond_horizon = 0

    for club in club_rows:
        if sval(club, "pbk16_club_identity_status") != "PBK16_EXACT_ALIAS_UNIQUE":
            continue
        key = (sval(club, "fixture_id"), sval(club, "player_id"))
        ev = evidence.get(key)
        if ev is None:
            missing_evidence += 1
            continue
        intl_dt = parse_dt(ev.get("kickoff_utc"))
        team_id = sval(club, "pbk16_team_id")
        if intl_dt is None or not team_id:
            missing_evidence += 1
            continue

        return_dt, fixture, return_status = next_played_domestic(domestic.get(team_id, []), intl_dt)
        if fixture is None:
            if return_status == "OUTSIDE_RETURN_HORIZON":
                return_beyond_horizon += 1
            else:
                missing_return += 1
            continue

        through = [
            row for dt, row in grouped[(key[1], sval(ev, "window_id"))]
            if dt <= intl_dt
        ]
        appearances = sum(bool_true(row, "appearance_confirmed") for row in through)
        minute_rows = [row for row in through if bool_true(row, "minutes_confirmed")]
        minutes = sum(as_int(row.get("minutes")) or 0 for row in minute_rows)

        current_minutes = as_int(ev.get("minutes")) if bool_true(ev, "minutes_confirmed") else None
        delta_hours = (return_dt - intl_dt).total_seconds() / 3600.0
        home_id = sval(fixture, "home_team_id")
        away_id = sval(fixture, "away_team_id")
        if team_id == home_id:
            club_side = "HOME"
            opponent_id = away_id
            opponent_name = sval(fixture, "away_team")
        elif team_id == away_id:
            club_side = "AWAY"
            opponent_id = home_id
            opponent_name = sval(fixture, "home_team")
        else:
            continue

        output.append({
            "international_fixture_id": key[0],
            "international_kickoff_utc": sval(ev, "kickoff_utc"),
            "window_id": sval(ev, "window_id"),
            "national_team_id": sval(ev, "national_team_id"),
            "national_team_name": sval(ev, "national_team_name"),
            "player_id": key[1],
            "player_name": sval(ev, "player_name"),
            "pbk16_team_id": team_id,
            "pbk16_team_name": sval(club, "pbk16_team_name"),
            "pbk16_provider_league_id": sval(club, "pbk16_provider_league_id"),
            "appearance_confirmed": "true" if bool_true(ev, "appearance_confirmed") else "false",
            "minutes_confirmed": "true" if bool_true(ev, "minutes_confirmed") else "false",
            "confirmed_minutes": "" if current_minutes is None else str(current_minutes),
            "window_direct_evidence_fixture_count_through_event": str(len(through)),
            "window_confirmed_appearances_through_event": str(appearances),
            "window_minutes_confirmed_fixture_count_through_event": str(len(minute_rows)),
            "window_confirmed_minutes_through_event": str(minutes),
            "next_domestic_fixture_id": sval(fixture, "fixture_id"),
            "next_domestic_kickoff_utc": sval(fixture, "kickoff_utc"),
            "next_domestic_home_team_id": home_id,
            "next_domestic_home_team": sval(fixture, "home_team"),
            "next_domestic_away_team_id": away_id,
            "next_domestic_away_team": sval(fixture, "away_team"),
            "club_side": club_side,
            "opponent_team_id": opponent_id,
            "opponent_team": opponent_name,
            "hours_to_next_domestic_fixture": f"{delta_hours:.3f}",
            "days_to_next_domestic_fixture": f"{delta_hours / 24.0:.4f}",
            "return_within_72h": "true" if delta_hours <= 72 else "false",
            "return_within_96h": "true" if delta_hours <= 96 else "false",
            "return_within_7d": "true" if delta_hours <= 168 else "false",
            "return_fixture_status": sval(fixture, "status"),
            "return_fixture_played_only": "true",
            "formal_callup_inferred": "false",
            "travel_inferred": "false",
            "current_club_used": "false",
            "fuzzy_matching_used": "false",
            "provider_calls": "0",
            "research_only": "true",
            "operational_betting_authority": "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })

    output.sort(key=lambda r: (
        r["next_domestic_kickoff_utc"],
        r["next_domestic_fixture_id"],
        r["pbk16_team_id"],
        r["player_id"],
        r["international_fixture_id"],
    ))
    return output, {
        "invalid_evidence_rows": invalid_evidence,
        "invalid_domestic_archive_rows": invalid_domestic,
        "mapped_rows_missing_direct_evidence": missing_evidence,
        "mapped_rows_without_later_played_domestic_fixture": missing_return,
        "mapped_rows_return_beyond_14d_horizon": return_beyond_horizon,
    }


def run(evidence_path=EVIDENCE, evidence_meta_path=EVIDENCE_META,
        club_path=CLUB_IDENTITY, club_meta_path=CLUB_META,
        archive_path=ARCHIVE, archive_meta_path=ARCHIVE_META,
        output_path=OUTPUT, meta_path=META):
    evidence_rows = read_csv(evidence_path)
    evidence_meta = read_json(evidence_meta_path)
    club_rows = read_csv(club_path)
    club_meta = read_json(club_meta_path)
    archive_rows = read_csv(archive_path)
    archive_meta = read_json(archive_meta_path)

    if not evidence_meta or evidence_meta.get("version") != EVIDENCE_VERSION:
        raise ValueError("direct player evidence contract not ready")
    if int(evidence_meta.get("evidence_rows") or 0) != len(evidence_rows):
        raise ValueError("direct player evidence row-count mismatch")
    if not club_meta or club_meta.get("version") != CLUB_VERSION or club_meta.get("status") != "OK":
        raise ValueError("PBK16 club identity contract not ready")
    if int(club_meta.get("output_rows") or 0) != len(club_rows):
        raise ValueError("PBK16 club identity row-count mismatch")
    if not archive_meta or archive_meta.get("version") != ARCHIVE_VERSION:
        raise ValueError("PBK16 all-competition archive contract not ready")
    if int(archive_meta.get("archive_rows") or 0) != len(archive_rows):
        raise ValueError("PBK16 all-competition archive row-count mismatch")

    rows, audit = build(evidence_rows, club_rows, archive_rows)
    keys = [
        (sval(r, "international_fixture_id"), sval(r, "player_id"), sval(r, "next_domestic_fixture_id"))
        for r in rows
    ]
    duplicate_rows = len(keys) - len(set(keys))
    invalid_output = sum(
        not (
            sval(r, "international_fixture_id")
            and sval(r, "player_id")
            and sval(r, "window_id")
            and sval(r, "pbk16_team_id")
            and sval(r, "next_domestic_fixture_id")
            and sval(r, "return_fixture_played_only") == "true"
            and sval(r, "formal_callup_inferred") == "false"
            and sval(r, "travel_inferred") == "false"
            and sval(r, "current_club_used") == "false"
            and sval(r, "fuzzy_matching_used") == "false"
            and sval(r, "provider_calls") == "0"
            and sval(r, "research_only") == "true"
            and sval(r, "operational_betting_authority") == "false"
        )
        for r in rows
    )
    counts = Counter()
    for row in rows:
        if sval(row, "return_within_72h") == "true":
            counts["RETURN_WITHIN_72H"] += 1
        if sval(row, "return_within_96h") == "true":
            counts["RETURN_WITHIN_96H"] += 1
        if sval(row, "return_within_7d") == "true":
            counts["RETURN_WITHIN_7D"] += 1
        if sval(row, "appearance_confirmed") == "true":
            counts["APPEARANCE_CONFIRMED"] += 1
        if sval(row, "minutes_confirmed") == "true":
            counts["MINUTES_CONFIRMED"] += 1

    mapped_input = sum(
        sval(r, "pbk16_club_identity_status") == "PBK16_EXACT_ALIAS_UNIQUE"
        for r in club_rows
    )
    meta = {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "OK" if rows and not duplicate_rows and not invalid_output else "ATTENTION",
        "direct_evidence_rows": len(evidence_rows),
        "direct_evidence_collection_status": evidence_meta.get("status"),
        "direct_evidence_collection_complete": evidence_meta.get("status") == "COMPLETE",
        "club_identity_rows": len(club_rows),
        "mapped_pbk16_input_rows": mapped_input,
        "all_competition_archive_rows": len(archive_rows),
        "output_rows": len(rows),
        "unique_players": len({sval(r, "player_id") for r in rows}),
        "unique_return_domestic_fixtures": len({sval(r, "next_domestic_fixture_id") for r in rows}),
        "duplicate_output_rows": duplicate_rows,
        "invalid_output_rows": invalid_output,
        "feature_counts": dict(sorted(counts.items())),
        **audit,
        "direct_evidence_only": True,
        "played_domestic_return_fixture_only": True,
        "max_return_horizon_hours": MAX_RETURN_HORIZON_HOURS,
        "return_horizon_fail_closed": True,
        "nationality_used_as_duty_evidence": False,
        "formal_callup_inferred": False,
        "travel_inferred": False,
        "current_club_used": False,
        "fuzzy_matching_used": False,
        "provider_calls": 0,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "next_stage": "After durable coverage review, join return-load features to historical market anchors for descriptive research.",
    }
    write_csv(output_path, rows)
    write_json(meta_path, meta)
    return meta


def main():
    print(json.dumps(run(), ensure_ascii=False))


if __name__ == "__main__":
    main()
