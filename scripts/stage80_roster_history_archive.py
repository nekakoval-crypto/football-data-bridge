#!/usr/bin/env python3
"""Stage 80 — append-only historical roster archive foundation.

Stage79 intentionally keeps one current roster snapshot per team for fast Match Card
reads. Stage80 preserves every distinct captured roster snapshot so PBK can later
answer historical questions such as who belonged to a squad at a given point in
time without asking the provider again.

This stage is provider-free. It reads already captured ``team_rosters.csv`` and
appends immutable rows to ``team_roster_history.csv``. Existing archive rows are
never replaced, and rerunning the same current snapshot is idempotent.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
CURRENT = OPS / "team_rosters.csv"
HISTORY = OPS / "team_roster_history.csv"
META = OPS / "stage80_last_run.json"
ARCHIVE_VERSION = "PBK_STAGE80_ROSTER_HISTORY_V1"

HISTORY_FIELDS = [
    "team_id", "team_name", "captured_at_utc", "player_id", "player_name",
    "age", "number", "position", "photo_url", "source", "archive_version",
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
        str(row.get("team_id") or "").strip(),
        str(row.get("captured_at_utc") or "").strip(),
        str(row.get("player_id") or "").strip(),
    )


def valid_snapshot_row(row):
    key = archive_key(row)
    return all(key)


def normalize_archive_row(row):
    return {
        "team_id": str(row.get("team_id") or "").strip(),
        "team_name": row.get("team_name"),
        "captured_at_utc": str(row.get("captured_at_utc") or "").strip(),
        "player_id": str(row.get("player_id") or "").strip(),
        "player_name": row.get("player_name"),
        "age": row.get("age"),
        "number": row.get("number"),
        "position": row.get("position"),
        "photo_url": row.get("photo_url"),
        "source": row.get("source") or "stage79:team_rosters",
        "archive_version": row.get("archive_version") or ARCHIVE_VERSION,
    }


def append_snapshots(existing, current):
    """Append only unseen team+capture+player rows and preserve prior bytes semantically.

    If a duplicate key is presented with different mutable values, the existing row
    wins. This is deliberate: historical observations are immutable after capture.
    """
    merged = {}
    invalid_existing = 0
    for row in existing:
        if not valid_snapshot_row(row):
            invalid_existing += 1
            continue
        normalized = normalize_archive_row(row)
        merged[archive_key(normalized)] = normalized

    added = 0
    invalid_current = 0
    duplicate_current = 0
    for row in current:
        if not valid_snapshot_row(row):
            invalid_current += 1
            continue
        normalized = normalize_archive_row(row)
        key = archive_key(normalized)
        if key in merged:
            duplicate_current += 1
            continue
        merged[key] = normalized
        added += 1

    rows = [merged[key] for key in sorted(merged)]
    return {
        "rows": rows,
        "added_rows": added,
        "duplicate_current_rows": duplicate_current,
        "invalid_current_rows": invalid_current,
        "invalid_existing_rows": invalid_existing,
    }


def snapshot_count(rows):
    return len({(str(row.get("team_id") or ""), str(row.get("captured_at_utc") or "")) for row in rows if valid_snapshot_row(row)})


def main():
    now = datetime.now(timezone.utc)
    current = read_csv(CURRENT)
    existing = read_csv(HISTORY)
    result = append_snapshots(existing, current)

    if result["rows"] or HISTORY.exists() or current:
        write_csv_atomic(HISTORY, HISTORY_FIELDS, result["rows"])

    meta = {
        "version": ARCHIVE_VERSION,
        "run_at_utc": iso(now),
        "status": "OK" if not result["invalid_existing_rows"] else "ATTENTION",
        "provider_calls": 0,
        "current_roster_rows_seen": len(current),
        "history_rows_before": len(existing),
        "history_rows_after": len(result["rows"]),
        "history_snapshots_after": snapshot_count(result["rows"]),
        "added_rows": result["added_rows"],
        "duplicate_current_rows": result["duplicate_current_rows"],
        "invalid_current_rows": result["invalid_current_rows"],
        "invalid_existing_rows": result["invalid_existing_rows"],
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
