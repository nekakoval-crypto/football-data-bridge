#!/usr/bin/env python3
"""Stage80 — provider-free normalized lineup and injury archives.

Sources are already-persisted PBK evidence:
- match_context_snapshots.csv (Stage55 official lineup/injury context)
- rotation_snapshots.csv (official lineup/formation rotation evidence)

This stage performs no provider I/O and never creates betting/model authority.
It materializes append-only normalized evidence ledgers:
- lineup_snapshots.csv: one team lineup observation per fixture/snapshot/team/source
- injury_snapshots.csv: one deduplicated injury observation per fixture/snapshot/player/type/reason
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
CONTEXT = OPS / "match_context_snapshots.csv"
ROTATION = OPS / "rotation_snapshots.csv"
LINEUPS = OPS / "lineup_snapshots.csv"
INJURIES = OPS / "injury_snapshots.csv"
META = OPS / "stage80_lineup_injury_archive_last_run.json"
VERSION = "PBK_STAGE80_LINEUP_INJURY_ARCHIVE_V1"

LINEUP_FIELDS = [
    "fixture_id", "captured_at_utc", "kickoff_utc", "team_id", "team_name",
    "side", "formation", "coach", "starting_xi_json", "starting_xi_count",
    "source_dataset", "source_snapshot_type", "official_lineup",
    "archive_version",
]
INJURY_FIELDS = [
    "fixture_id", "captured_at_utc", "kickoff_utc", "team_id", "team_name",
    "player_id", "player_name", "availability_type", "reason",
    "source_dataset", "source_snapshot_type", "archive_version",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def parse_json_list(value):
    if value in (None, ""):
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_xi(value):
    output = []
    seen = set()
    for item in parse_json_list(value):
        if not isinstance(item, dict):
            continue
        player = item.get("player") if isinstance(item.get("player"), dict) else item
        pid = str(player.get("id") or player.get("player_id") or "").strip()
        name = str(player.get("name") or player.get("player_name") or "").strip()
        dedupe = pid or name
        if not dedupe or dedupe in seen:
            continue
        seen.add(dedupe)
        output.append({
            "id": pid or None,
            "name": name or None,
            "number": player.get("number"),
            "pos": player.get("pos") or player.get("position") or None,
            "grid": player.get("grid") or None,
        })
    return output


def lineup_key(row):
    return (
        sval(row, "fixture_id"),
        sval(row, "captured_at_utc"),
        sval(row, "team_id"),
        sval(row, "source_dataset"),
    )


def injury_key(row):
    return (
        sval(row, "fixture_id"),
        sval(row, "captured_at_utc"),
        sval(row, "team_id"),
        sval(row, "player_id") or sval(row, "player_name"),
        sval(row, "availability_type"),
        sval(row, "reason"),
        sval(row, "source_dataset"),
    )


def append_first_observation(existing, candidates, key_fn):
    merged = {}
    invalid_existing = 0
    duplicate_existing = 0
    for row in existing:
        key = key_fn(row)
        if not all(key):
            invalid_existing += 1
            continue
        if key in merged:
            duplicate_existing += 1
            continue
        merged[key] = dict(row)

    added = 0
    duplicate_candidates = 0
    invalid_candidates = 0
    for row in candidates:
        key = key_fn(row)
        if not all(key):
            invalid_candidates += 1
            continue
        if key in merged:
            duplicate_candidates += 1
            continue
        merged[key] = dict(row)
        added += 1

    return {
        "rows": [merged[key] for key in sorted(merged)],
        "added_rows": added,
        "duplicate_candidates": duplicate_candidates,
        "duplicate_existing": duplicate_existing,
        "invalid_candidates": invalid_candidates,
        "invalid_existing": invalid_existing,
    }


def context_lineup_candidates(rows):
    out = []
    for row in rows:
        if sval(row, "lineups_available").upper() not in {"YES", "TRUE", "1"}:
            continue
        fixture_id = sval(row, "api_fixture_id")
        captured = sval(row, "captured_at_utc")
        kickoff = sval(row, "current_kickoff_utc")
        snapshot_type = sval(row, "snapshot_type")
        for side in ("home", "away"):
            xi = normalize_xi(row.get(f"{side}_start_xi_json"))
            if not xi:
                continue
            out.append({
                "fixture_id": fixture_id,
                "captured_at_utc": captured,
                "kickoff_utc": kickoff,
                "team_id": sval(row, f"{side}_team_id"),
                "team_name": row.get(f"{side}_team") or "",
                "side": side.upper(),
                "formation": row.get(f"{side}_formation") or "",
                "coach": row.get(f"{side}_coach") or "",
                "starting_xi_json": canonical_json(xi),
                "starting_xi_count": str(len(xi)),
                "source_dataset": "match_context_snapshots",
                "source_snapshot_type": snapshot_type,
                "official_lineup": "YES",
                "archive_version": VERSION,
            })
    return out


def rotation_lineup_candidates(rows):
    out = []
    for row in rows:
        if sval(row, "current_lineups_available").upper() not in {"YES", "TRUE", "1"}:
            continue
        fixture_id = sval(row, "api_fixture_id")
        captured = sval(row, "captured_at_utc")
        kickoff = sval(row, "kickoff_utc")
        for side in ("home", "away"):
            xi = normalize_xi(row.get(f"{side}_current_xi_json"))
            if not xi:
                continue
            out.append({
                "fixture_id": fixture_id,
                "captured_at_utc": captured,
                "kickoff_utc": kickoff,
                "team_id": sval(row, f"{side}_team_id"),
                "team_name": row.get(f"{side}_team") or "",
                "side": side.upper(),
                "formation": row.get(f"{side}_current_formation") or "",
                "coach": row.get(f"{side}_current_coach") or "",
                "starting_xi_json": canonical_json(xi),
                "starting_xi_count": str(len(xi)),
                "source_dataset": "rotation_snapshots",
                "source_snapshot_type": "ROTATION",
                "official_lineup": "YES",
                "archive_version": VERSION,
            })
    return out


def injury_candidates(rows):
    out = []
    for row in rows:
        fixture_id = sval(row, "api_fixture_id")
        captured = sval(row, "captured_at_utc")
        kickoff = sval(row, "current_kickoff_utc")
        snapshot_type = sval(row, "snapshot_type")
        seen = set()
        for item in parse_json_list(row.get("injuries_json")):
            if not isinstance(item, dict):
                continue
            team_id = str(item.get("team_id") or "").strip()
            team_name = str(item.get("team") or "").strip()
            player_id = str(item.get("player_id") or item.get("id") or "").strip()
            player_name = str(item.get("player") or item.get("name") or "").strip()
            availability_type = str(item.get("type") or "").strip()
            reason = str(item.get("reason") or "").strip()
            dedupe = (team_id, player_id or player_name, availability_type, reason)
            if dedupe in seen:
                continue
            seen.add(dedupe)
            out.append({
                "fixture_id": fixture_id,
                "captured_at_utc": captured,
                "kickoff_utc": kickoff,
                "team_id": team_id,
                "team_name": team_name,
                "player_id": player_id,
                "player_name": player_name,
                "availability_type": availability_type,
                "reason": reason,
                "source_dataset": "match_context_snapshots",
                "source_snapshot_type": snapshot_type,
                "archive_version": VERSION,
            })
    return out


def build_archives(context_rows, rotation_rows, existing_lineups=None, existing_injuries=None):
    lineup_candidates = context_lineup_candidates(context_rows) + rotation_lineup_candidates(rotation_rows)
    injury_rows = injury_candidates(context_rows)
    lineups = append_first_observation(existing_lineups or [], lineup_candidates, lineup_key)
    injuries = append_first_observation(existing_injuries or [], injury_rows, injury_key)
    return lineups, injuries


def main():
    context_rows = read_csv(CONTEXT)
    rotation_rows = read_csv(ROTATION)
    existing_lineups = read_csv(LINEUPS)
    existing_injuries = read_csv(INJURIES)
    lineups, injuries = build_archives(context_rows, rotation_rows, existing_lineups, existing_injuries)

    write_csv_atomic(LINEUPS, LINEUP_FIELDS, lineups["rows"])
    write_csv_atomic(INJURIES, INJURY_FIELDS, injuries["rows"])

    status = "ATTENTION" if any([
        lineups["invalid_existing"], lineups["invalid_candidates"],
        injuries["invalid_existing"], injuries["invalid_candidates"],
    ]) else "OK"
    meta = {
        "version": VERSION,
        "run_at_utc": iso_now(),
        "status": status,
        "provider_calls": 0,
        "source_context_rows": len(context_rows),
        "source_rotation_rows": len(rotation_rows),
        "lineup_rows_before": len(existing_lineups),
        "lineup_rows_after": len(lineups["rows"]),
        "lineup_rows_added": lineups["added_rows"],
        "injury_rows_before": len(existing_injuries),
        "injury_rows_after": len(injuries["rows"]),
        "injury_rows_added": injuries["added_rows"],
        "lineup_identity": "fixture_id+captured_at_utc+team_id+source_dataset",
        "injury_identity": "fixture_id+captured_at_utc+team_id+(player_id|player_name)+availability_type+reason+source_dataset",
        "append_only_first_observation_wins": True,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    if status == "ATTENTION":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
