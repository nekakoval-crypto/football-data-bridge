#!/usr/bin/env python3
"""Stage80 — exact identity join for direct international-duty player evidence.

Joins API-Football player IDs from direct national-team fixture evidence to:
1) PBK historical_players.csv by exact player_id only;
2) safe PBK -> Transfermarkt identity rows (AUTO_MATCH + HIGH) by the same PBK ID.

No fuzzy/name matching is allowed here. Names are descriptive only.
This layer does not derive the player's club at the international fixture date;
that is a later temporal transfer-history step.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
EVIDENCE = OPS / "international_duty_player_evidence.csv"
EVIDENCE_META = OPS / "stage80_international_duty_player_evidence_capture_last_run.json"
HISTORICAL_PLAYERS = OPS / "historical_players.csv"
HISTORICAL_PLAYERS_META = OPS / "stage80_player_catalog_last_run.json"
TRANSFER_IDENTITY = OPS / "pbk_transfermarkt_player_identity.csv"

OUTPUT = OPS / "international_duty_player_identity_join.csv"
META = OPS / "stage80_international_duty_player_identity_join_last_run.json"

VERSION = "PBK_STAGE80_INTERNATIONAL_DUTY_PLAYER_IDENTITY_JOIN_V1_EXACT_ID_ONLY"
EVIDENCE_VERSION = "PBK_STAGE80_INTERNATIONAL_DUTY_PLAYER_EVIDENCE_CAPTURE_V2_STRICT_ROLE_SEMANTICS"
CATALOG_VERSION = "PBK_STAGE80_HISTORICAL_PLAYER_CATALOG_V1"

FIELDS = [
    "player_id","latest_international_player_name",
    "international_evidence_rows","international_fixture_count",
    "international_team_count","international_team_ids","international_team_names",
    "first_international_kickoff_utc","last_international_kickoff_utc",
    "appearance_fixture_count","minutes_confirmed_fixture_count",
    "confirmed_minutes_total","substitute_appearance_fixture_count",
    "pbk_catalog_match_status","pbk_catalog_identity_method",
    "pbk_latest_observed_name","pbk_latest_observed_position",
    "pbk_first_seen_at_utc","pbk_last_seen_at_utc",
    "pbk_has_roster_evidence","pbk_has_match_stats_evidence",
    "pbk_latest_roster_team_ids","pbk_latest_roster_team_names",
    "transfermarkt_identity_status","transfermarkt_player_id",
    "transfermarkt_player_name","transfermarkt_mapping_method",
    "transfermarkt_mapping_confidence","transfermarkt_match_status",
    "club_at_fixture_date_status",
    "identity_contract","fuzzy_matching_used","name_used_for_identity",
    "provider_calls","research_only","operational_betting_authority",
    "creates_signal","probability_mutation","eligibility_mutation",
    "stake_changes","forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def as_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        try:
            return int(float(str(value).strip()))
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
    except (OSError, UnicodeError, json.JSONDecodeError):
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


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z","+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def valid_evidence_row(row):
    minutes = as_int(row.get("minutes"))
    if sval(row, "minutes_confirmed") == "true" and minutes is None:
        return False
    return bool(
        sval(row, "fixture_id")
        and sval(row, "player_id")
        and sval(row, "national_team_id")
        and parse_dt(row.get("kickoff_utc")) is not None
        and sval(row, "matchday_squad_confirmed") == "true"
        and sval(row, "formal_callup_status") == "NOT_SEPARATELY_VERIFIED"
        and sval(row, "travel_status") == "NOT_DERIVED"
        and sval(row, "nationality_inference_allowed") == "false"
        and sval(row, "travel_inference_allowed") == "false"
        and sval(row, "research_only") == "true"
        and sval(row, "operational_betting_authority") == "false"
        and sval(row, "creates_signal") == "false"
        and sval(row, "probability_mutation") == "false"
        and sval(row, "eligibility_mutation") == "false"
        and sval(row, "stake_changes") == "false"
        and sval(row, "forward_journal_mutation") == "false"
    )


def unique_map(rows, key_field):
    out = {}
    duplicates = 0
    conflicts = 0
    for row in rows:
        key = sval(row, key_field)
        if not key:
            continue
        old = out.get(key)
        if old is None:
            out[key] = dict(row)
            continue
        duplicates += 1
        if old != row:
            conflicts += 1
    return out, duplicates, conflicts


def safe_transfer_map(rows):
    candidates = defaultdict(list)
    for row in rows:
        if (
            sval(row, "pbk_player_id")
            and sval(row, "transfermarkt_player_id")
            and sval(row, "mapping_confidence") == "HIGH"
            and sval(row, "match_status") == "AUTO_MATCH"
        ):
            candidates[sval(row, "pbk_player_id")].append(dict(row))

    out = {}
    duplicate_rows = 0
    conflict_players = 0
    for player_id, group in candidates.items():
        ids = {sval(r, "transfermarkt_player_id") for r in group}
        duplicate_rows += max(0, len(group) - 1)
        if len(ids) != 1:
            conflict_players += 1
            continue
        group.sort(key=lambda r: (
            sval(r, "mapping_method"),
            sval(r, "transfermarkt_player_id"),
            sval(r, "transfermarkt_player_name"),
        ))
        out[player_id] = group[0]
    return out, duplicate_rows, conflict_players


def validate_source_meta(evidence_meta, player_meta):
    return bool(
        evidence_meta
        and not evidence_meta.get("_invalid_json")
        and evidence_meta.get("version") == EVIDENCE_VERSION
        and evidence_meta.get("status") in {"COLLECTING","OK"}
        and int(evidence_meta.get("evidence_rows") or 0) > 0
        and int(evidence_meta.get("duplicate_evidence_rows") or 0) == 0
        and int(evidence_meta.get("invalid_evidence_rows") or 0) == 0
        and evidence_meta.get("player_stats_starter_inference_allowed") is False
        and evidence_meta.get("research_only") is True
        and evidence_meta.get("operational_betting_authority") is False
        and player_meta
        and not player_meta.get("_invalid_json")
        and player_meta.get("version") == CATALOG_VERSION
        and player_meta.get("status") == "OK"
        and int(player_meta.get("catalog_players") or 0) > 0
        and int(player_meta.get("invalid_roster_rows") or 0) == 0
        and int(player_meta.get("invalid_stats_rows") or 0) == 0
        and int(player_meta.get("provider_calls") or 0) == 0
    )


def aggregate(evidence_rows, player_catalog, transfer_map):
    grouped = defaultdict(list)
    invalid = 0
    for row in evidence_rows:
        if not valid_evidence_row(row):
            invalid += 1
            continue
        grouped[sval(row, "player_id")].append(dict(row))

    output = []
    for player_id in sorted(grouped, key=lambda x: (len(x), x)):
        rows = grouped[player_id]
        rows.sort(key=lambda r: (
            parse_dt(r.get("kickoff_utc")) or datetime.min.replace(tzinfo=timezone.utc),
            sval(r, "captured_at_utc"),
            sval(r, "fixture_id"),
        ))
        latest = rows[-1]

        fixture_ids = {sval(r, "fixture_id") for r in rows}
        team_pairs = sorted({
            (sval(r, "national_team_id"), sval(r, "national_team_name"))
            for r in rows if sval(r, "national_team_id")
        })
        appearance_fixtures = {
            sval(r, "fixture_id") for r in rows
            if sval(r, "appearance_confirmed") == "true"
        }
        minute_fixtures = {
            sval(r, "fixture_id") for r in rows
            if sval(r, "minutes_confirmed") == "true"
        }
        sub_fixtures = {
            sval(r, "fixture_id") for r in rows
            if sval(r, "substitute_appearance_confirmed") == "true"
        }
        minutes_total = sum(
            as_int(r.get("minutes")) or 0
            for r in rows if sval(r, "minutes_confirmed") == "true"
        )

        pbk = player_catalog.get(player_id)
        tm = transfer_map.get(player_id)
        output.append({
            "player_id": player_id,
            "latest_international_player_name": sval(latest, "player_name"),
            "international_evidence_rows": str(len(rows)),
            "international_fixture_count": str(len(fixture_ids)),
            "international_team_count": str(len(team_pairs)),
            "international_team_ids": ",".join(pair[0] for pair in team_pairs),
            "international_team_names": " | ".join(pair[1] for pair in team_pairs if pair[1]),
            "first_international_kickoff_utc": sval(rows[0], "kickoff_utc"),
            "last_international_kickoff_utc": sval(rows[-1], "kickoff_utc"),
            "appearance_fixture_count": str(len(appearance_fixtures)),
            "minutes_confirmed_fixture_count": str(len(minute_fixtures)),
            "confirmed_minutes_total": str(minutes_total),
            "substitute_appearance_fixture_count": str(len(sub_fixtures)),
            "pbk_catalog_match_status": "EXACT_ID_MATCH" if pbk else "UNMATCHED",
            "pbk_catalog_identity_method": "API_FOOTBALL_PLAYER_ID_EXACT" if pbk else "",
            "pbk_latest_observed_name": sval(pbk, "latest_observed_name"),
            "pbk_latest_observed_position": sval(pbk, "latest_observed_position"),
            "pbk_first_seen_at_utc": sval(pbk, "first_seen_at_utc"),
            "pbk_last_seen_at_utc": sval(pbk, "last_seen_at_utc"),
            "pbk_has_roster_evidence": sval(pbk, "has_roster_evidence"),
            "pbk_has_match_stats_evidence": sval(pbk, "has_match_stats_evidence"),
            "pbk_latest_roster_team_ids": sval(pbk, "latest_roster_team_ids"),
            "pbk_latest_roster_team_names": sval(pbk, "latest_roster_team_names"),
            "transfermarkt_identity_status": "SAFE_AUTO_HIGH" if tm else "UNMAPPED",
            "transfermarkt_player_id": sval(tm, "transfermarkt_player_id"),
            "transfermarkt_player_name": sval(tm, "transfermarkt_player_name"),
            "transfermarkt_mapping_method": sval(tm, "mapping_method"),
            "transfermarkt_mapping_confidence": sval(tm, "mapping_confidence"),
            "transfermarkt_match_status": sval(tm, "match_status"),
            "club_at_fixture_date_status": "NOT_DERIVED",
            "identity_contract": "EXACT_API_FOOTBALL_PLAYER_ID",
            "fuzzy_matching_used": "false",
            "name_used_for_identity": "false",
            "provider_calls": "0",
            "research_only": "true",
            "operational_betting_authority": "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })
    return output, invalid


def run(
    evidence_path=EVIDENCE,
    evidence_meta_path=EVIDENCE_META,
    players_path=HISTORICAL_PLAYERS,
    players_meta_path=HISTORICAL_PLAYERS_META,
    transfer_identity_path=TRANSFER_IDENTITY,
    output_path=OUTPUT,
    meta_path=META,
):
    evidence_rows = read_csv(evidence_path)
    evidence_meta = read_json(evidence_meta_path)
    player_rows = read_csv(players_path)
    player_meta = read_json(players_meta_path)
    transfer_rows = read_csv(transfer_identity_path)

    if not validate_source_meta(evidence_meta, player_meta):
        raise ValueError("international evidence or PBK player catalog source contract is not ready")
    if int(evidence_meta.get("evidence_rows") or 0) != len(evidence_rows):
        raise ValueError("international evidence row count does not match capture meta")
    if int(player_meta.get("catalog_players") or 0) != len(player_rows):
        raise ValueError("historical player catalog row count does not match catalog meta")

    player_catalog, player_duplicates, player_conflicts = unique_map(player_rows, "player_id")
    if player_duplicates or player_conflicts:
        raise ValueError(
            f"historical player catalog must be unique by player_id; "
            f"duplicates={player_duplicates}, conflicts={player_conflicts}"
        )

    transfer_map, transfer_duplicate_rows, transfer_conflict_players = safe_transfer_map(transfer_rows)
    if transfer_conflict_players:
        raise ValueError(
            f"conflicting safe Transfermarkt identities for {transfer_conflict_players} PBK players"
        )

    output, invalid_evidence_rows = aggregate(evidence_rows, player_catalog, transfer_map)

    output_ids = [sval(row, "player_id") for row in output]
    duplicate_output_players = len(output_ids) - len(set(output_ids))
    exact_catalog_matches = sum(
        sval(row, "pbk_catalog_match_status") == "EXACT_ID_MATCH" for row in output
    )
    tm_matches = sum(
        sval(row, "transfermarkt_identity_status") == "SAFE_AUTO_HIGH" for row in output
    )
    both_matches = sum(
        sval(row, "pbk_catalog_match_status") == "EXACT_ID_MATCH"
        and sval(row, "transfermarkt_identity_status") == "SAFE_AUTO_HIGH"
        for row in output
    )
    invalid_output_rows = sum(
        not (
            sval(row, "player_id")
            and sval(row, "identity_contract") == "EXACT_API_FOOTBALL_PLAYER_ID"
            and sval(row, "fuzzy_matching_used") == "false"
            and sval(row, "name_used_for_identity") == "false"
            and sval(row, "club_at_fixture_date_status") == "NOT_DERIVED"
            and sval(row, "provider_calls") == "0"
            and sval(row, "research_only") == "true"
            and sval(row, "operational_betting_authority") == "false"
            and sval(row, "creates_signal") == "false"
        )
        for row in output
    )

    total_players = len(output)
    status = "OK" if (
        total_players > 0
        and invalid_evidence_rows == 0
        and duplicate_output_players == 0
        and invalid_output_rows == 0
    ) else "ATTENTION"

    meta = {
        "version": VERSION,
        "generated_at_utc": iso_now(),
        "status": status,
        "evidence_rows": len(evidence_rows),
        "valid_evidence_rows": len(evidence_rows) - invalid_evidence_rows,
        "invalid_evidence_rows": invalid_evidence_rows,
        "international_evidence_players": total_players,
        "historical_player_catalog_rows": len(player_rows),
        "historical_player_catalog_unique_players": len(player_catalog),
        "historical_player_catalog_duplicate_rows": player_duplicates,
        "historical_player_catalog_conflicts": player_conflicts,
        "exact_pbk_catalog_matched_players": exact_catalog_matches,
        "pbk_catalog_unmatched_players": total_players - exact_catalog_matches,
        "exact_pbk_catalog_player_coverage_pct": round(
            exact_catalog_matches / total_players * 100.0, 4
        ) if total_players else 0.0,
        "transfer_identity_source_rows": len(transfer_rows),
        "safe_transfer_identity_players": len(transfer_map),
        "safe_transfer_identity_duplicate_rows": transfer_duplicate_rows,
        "safe_transfer_identity_conflict_players": transfer_conflict_players,
        "international_players_with_safe_transfer_identity": tm_matches,
        "safe_transfer_identity_coverage_pct": round(
            tm_matches / total_players * 100.0, 4
        ) if total_players else 0.0,
        "international_players_with_catalog_and_transfer_identity": both_matches,
        "output_rows": len(output),
        "duplicate_output_players": duplicate_output_players,
        "invalid_output_rows": invalid_output_rows,
        "identity_contract": "EXACT_API_FOOTBALL_PLAYER_ID",
        "exact_id_only": True,
        "fuzzy_matching_used": False,
        "name_used_for_identity": False,
        "club_at_fixture_date_derived": False,
        "current_club_substituted_for_historical_club": False,
        "provider_calls": 0,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "next_stage": (
            "Use safe Transfermarkt identities plus historical transfer events to derive "
            "club-at-international-fixture-date, without substituting current club."
        ),
    }

    write_csv(output_path, output)
    write_json(meta_path, meta)
    return meta


def main():
    print(json.dumps(run(), ensure_ascii=False))


if __name__ == "__main__":
    main()
