#!/usr/bin/env python3
"""Stage80 — append-only historical fixture observation archive.

`current_round_fixtures.csv` is deliberately a rolling read model. This provider-
free stage preserves every distinct fixture observation already captured by
Stage71 so older rounds/status snapshots do not disappear when the rolling
inventory advances.

Identity is `fixture_id + observed_at_utc`. Existing historical observations are
immutable; rerunning the same current-round snapshot is idempotent.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
CURRENT = OPS / "current_round_fixtures.csv"
HISTORY = OPS / "fixture_history_snapshots.csv"
META = OPS / "stage80_fixture_history_last_run.json"
ARCHIVE_VERSION = "PBK_STAGE80_FIXTURE_HISTORY_V1"

HISTORY_FIELDS = [
    "fixture_id", "provider_league_id", "league_name", "country",
    "country_flag_url", "league_logo_url", "season", "round", "kickoff_utc",
    "home_team", "home_team_logo_url", "away_team", "away_team_logo_url",
    "referee", "venue_name", "venue_city",
    "status", "source_status", "score_home", "score_away", "observed_at_utc",
    "archive_version",
]


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def archive_key(row):
    return (
        str(row.get("fixture_id") or "").strip(),
        str(row.get("observed_at_utc") or "").strip(),
    )


def valid_row(row):
    return all(archive_key(row))


def normalize(row):
    return {
        "fixture_id": str(row.get("fixture_id") or "").strip(),
        "provider_league_id": str(row.get("provider_league_id") or "").strip(),
        "league_name": row.get("league_name"),
        "country": row.get("country"),
        "country_flag_url": row.get("country_flag_url"),
        "league_logo_url": row.get("league_logo_url"),
        "season": row.get("season"),
        "round": row.get("round"),
        "kickoff_utc": row.get("kickoff_utc"),
        "home_team": row.get("home_team"),
        "home_team_logo_url": row.get("home_team_logo_url"),
        "away_team": row.get("away_team"),
        "away_team_logo_url": row.get("away_team_logo_url"),
        "referee": row.get("referee"),
        "venue_name": row.get("venue_name"),
        "venue_city": row.get("venue_city"),
        "status": row.get("status"),
        "source_status": row.get("source_status"),
        "score_home": row.get("score_home"),
        "score_away": row.get("score_away"),
        "observed_at_utc": str(row.get("observed_at_utc") or "").strip(),
        "archive_version": row.get("archive_version") or ARCHIVE_VERSION,
    }


def append_observations(existing, current):
    merged = {}
    invalid_existing = 0
    duplicate_existing = 0
    for row in existing:
        if not valid_row(row):
            invalid_existing += 1
            continue
        normalized = normalize(row)
        key = archive_key(normalized)
        if key in merged:
            duplicate_existing += 1
            continue
        merged[key] = normalized

    added = 0
    duplicates = 0
    invalid_current = 0
    for row in current:
        if not valid_row(row):
            invalid_current += 1
            continue
        normalized = normalize(row)
        key = archive_key(normalized)
        if key in merged:
            duplicates += 1
            continue
        merged[key] = normalized
        added += 1

    rows = [merged[key] for key in sorted(merged)]
    return {
        "rows": rows,
        "added_rows": added,
        "duplicate_current_rows": duplicates,
        "duplicate_existing_rows": duplicate_existing,
        "invalid_current_rows": invalid_current,
        "invalid_existing_rows": invalid_existing,
    }


def inventory(rows):
    fixture_ids = {str(row.get("fixture_id") or "").strip() for row in rows if valid_row(row)}
    snapshots = {archive_key(row) for row in rows if valid_row(row)}
    observation_times = {str(row.get("observed_at_utc") or "").strip() for row in rows if valid_row(row)}
    return {
        "unique_fixtures": len(fixture_ids),
        "fixture_observations": len(snapshots),
        "observation_runs": len(observation_times),
    }


def main():
    now = datetime.now(timezone.utc)
    current = read_csv(CURRENT)
    existing = read_csv(HISTORY)
    result = append_observations(existing, current)

    if result["rows"] or HISTORY.exists() or current:
        write_csv_atomic(HISTORY, HISTORY_FIELDS, result["rows"])

    counts = inventory(result["rows"])
    status = "ATTENTION" if result["invalid_existing_rows"] or result["invalid_current_rows"] else "OK"
    meta = {
        "version": ARCHIVE_VERSION,
        "run_at_utc": iso(now),
        "status": status,
        "provider_calls": 0,
        "current_fixture_rows_seen": len(current),
        "history_rows_before": len(existing),
        "history_rows_after": len(result["rows"]),
        **counts,
        "added_rows": result["added_rows"],
        "duplicate_current_rows": result["duplicate_current_rows"],
        "duplicate_existing_rows": result["duplicate_existing_rows"],
        "invalid_current_rows": result["invalid_current_rows"],
        "invalid_existing_rows": result["invalid_existing_rows"],
        "identity": "fixture_id+observed_at_utc",
        "append_only": True,
        "research_reference_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
