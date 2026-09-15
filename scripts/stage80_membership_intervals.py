#!/usr/bin/env python3
"""Stage 80 — provider-free observed roster membership intervals.

The append-only ``team_roster_history.csv`` is the evidence source. This module
builds a deterministic projection describing contiguous *observed* roster
presence for each team/player across captured snapshots.

Important: snapshot boundaries are not transfer dates. An observed absence closes
an observed interval, but PBK must not relabel it as a confirmed transfer without
separate transfer-source evidence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
HISTORY = OPS / "team_roster_history.csv"
INTERVALS = OPS / "team_membership_intervals.csv"
META = OPS / "stage80_membership_last_run.json"
VERSION = "PBK_STAGE80_MEMBERSHIP_INTERVALS_V1"

FIELDS = [
    "interval_id", "team_id", "team_name", "player_id", "player_name",
    "position", "interval_index", "first_seen_at_utc", "last_seen_at_utc",
    "prior_absent_at_utc", "next_absent_at_utc", "observed_snapshot_count",
    "interval_status", "current_in_latest_snapshot", "source",
    "evidence_semantics", "archive_version",
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


def valid_row(row):
    return all(str(row.get(field) or "").strip() for field in ("team_id", "player_id", "captured_at_utc"))


def interval_id(team_id, player_id, first_seen):
    raw = f"{team_id}|{player_id}|{first_seen}|{VERSION}".encode("utf-8")
    return "membership:" + hashlib.sha256(raw).hexdigest()[:24]


def _emit_interval(team_id, snapshots, player_id, interval_index, start_idx, end_idx, player_rows):
    first_seen = snapshots[start_idx]
    last_seen = snapshots[end_idx]
    prior_absent = snapshots[start_idx - 1] if start_idx > 0 else ""
    next_absent = snapshots[end_idx + 1] if end_idx + 1 < len(snapshots) else ""
    latest = snapshots[-1]
    current = end_idx == len(snapshots) - 1
    last_row = player_rows[last_seen]
    present_count = sum(1 for idx in range(start_idx, end_idx + 1) if snapshots[idx] in player_rows)
    return {
        "interval_id": interval_id(team_id, player_id, first_seen),
        "team_id": team_id,
        "team_name": last_row.get("team_name"),
        "player_id": player_id,
        "player_name": last_row.get("player_name"),
        "position": last_row.get("position"),
        "interval_index": str(interval_index),
        "first_seen_at_utc": first_seen,
        "last_seen_at_utc": last_seen,
        "prior_absent_at_utc": prior_absent,
        "next_absent_at_utc": next_absent,
        "observed_snapshot_count": str(present_count),
        "interval_status": "OPEN_LATEST" if current else "CLOSED_BY_OBSERVED_ABSENCE",
        "current_in_latest_snapshot": "true" if current else "false",
        "source": "derived:team_roster_history",
        "evidence_semantics": "OBSERVED_ROSTER_PRESENCE_NOT_CONFIRMED_TRANSFER_DATE",
        "archive_version": VERSION,
    }


def build_intervals(rows):
    """Build deterministic contiguous presence intervals per team/player.

    Duplicate rows inside the same team snapshot collapse by player_id. Invalid
    rows are excluded and reported; source evidence is never mutated here.
    """
    grouped = defaultdict(lambda: defaultdict(dict))
    invalid = 0
    duplicate_snapshot_players = 0
    for row in rows:
        if not valid_row(row):
            invalid += 1
            continue
        team_id = str(row.get("team_id") or "").strip()
        player_id = str(row.get("player_id") or "").strip()
        captured = str(row.get("captured_at_utc") or "").strip()
        if player_id in grouped[team_id][captured]:
            duplicate_snapshot_players += 1
            continue
        grouped[team_id][captured][player_id] = dict(row)

    output = []
    team_count = 0
    snapshot_count = 0
    for team_id in sorted(grouped):
        snapshots = sorted(grouped[team_id])
        if not snapshots:
            continue
        team_count += 1
        snapshot_count += len(snapshots)
        all_players = sorted({pid for snap in snapshots for pid in grouped[team_id][snap]})
        for player_id in all_players:
            player_rows = {
                snap: grouped[team_id][snap][player_id]
                for snap in snapshots
                if player_id in grouped[team_id][snap]
            }
            start_idx = None
            interval_index = 0
            for idx, snap in enumerate(snapshots):
                present = snap in player_rows
                if present and start_idx is None:
                    start_idx = idx
                if not present and start_idx is not None:
                    interval_index += 1
                    output.append(_emit_interval(
                        team_id, snapshots, player_id, interval_index,
                        start_idx, idx - 1, player_rows,
                    ))
                    start_idx = None
            if start_idx is not None:
                interval_index += 1
                output.append(_emit_interval(
                    team_id, snapshots, player_id, interval_index,
                    start_idx, len(snapshots) - 1, player_rows,
                ))

    output.sort(key=lambda row: (
        row["team_id"], row["player_id"], row["first_seen_at_utc"], row["interval_id"]
    ))
    return {
        "rows": output,
        "teams": team_count,
        "snapshots": snapshot_count,
        "invalid_history_rows": invalid,
        "duplicate_snapshot_players": duplicate_snapshot_players,
    }


def main():
    history = read_csv(HISTORY)
    result = build_intervals(history)
    if result["rows"] or INTERVALS.exists() or history:
        write_csv_atomic(INTERVALS, FIELDS, result["rows"])
    meta = {
        "version": VERSION,
        "run_at_utc": iso(),
        "status": "ATTENTION" if result["invalid_history_rows"] else "OK",
        "provider_calls": 0,
        "history_rows": len(history),
        "teams": result["teams"],
        "snapshots": result["snapshots"],
        "membership_intervals": len(result["rows"]),
        "invalid_history_rows": result["invalid_history_rows"],
        "duplicate_snapshot_players": result["duplicate_snapshot_players"],
        "exact_transfer_dates_claimed": False,
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
