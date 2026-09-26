#!/usr/bin/env python3
"""Stage80 — normalized historical player catalog.

Provider-free deterministic projection over already persisted roster-history and
player-match-stat evidence. Evidence ledgers remain authoritative; this catalog is
only a rebuildable warehouse convenience layer and never infers transfer dates or
current-team truth from stale observations.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from player_snapshot_store import read_snapshot_rows

OPS = Path(os.getenv("OPS_DIR", "ops"))
ROSTERS = OPS / "team_roster_history.csv"
STATS = OPS / "player_stats_snapshots.csv"
CATALOG = OPS / "historical_players.csv"
META = OPS / "stage80_player_catalog_last_run.json"
VERSION = "PBK_STAGE80_HISTORICAL_PLAYER_CATALOG_V1"

FIELDS = [
    "player_id", "latest_observed_name", "latest_observed_position",
    "latest_observed_age", "latest_observed_number", "latest_observed_photo_url",
    "first_seen_at_utc", "last_seen_at_utc", "latest_roster_seen_at_utc",
    "latest_stats_seen_at_utc", "roster_observation_rows", "roster_team_count",
    "latest_roster_team_ids", "latest_roster_team_names", "stats_fixture_count",
    "stats_row_count", "has_roster_evidence", "has_match_stats_evidence",
    "evidence_sources", "source", "projection_version",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv_atomic(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def valid_player_row(row):
    return bool(sval(row, "player_id"))


def evidence_stamp(row, source):
    return sval(row, "captured_at_utc" if source == "roster" else "observed_at_utc")


def build_catalog(roster_rows, stats_rows):
    grouped = defaultdict(lambda: {"roster": [], "stats": []})
    invalid_roster = 0
    invalid_stats = 0

    for row in roster_rows:
        if not valid_player_row(row):
            invalid_roster += 1
            continue
        grouped[sval(row, "player_id")]["roster"].append(dict(row))
    for row in stats_rows:
        if not valid_player_row(row):
            invalid_stats += 1
            continue
        grouped[sval(row, "player_id")]["stats"].append(dict(row))

    output = []
    for player_id in sorted(grouped, key=lambda value: (len(value), value)):
        roster = grouped[player_id]["roster"]
        stats = grouped[player_id]["stats"]
        evidence = []
        for row in roster:
            evidence.append((evidence_stamp(row, "roster"), 1, "roster", row))
        for row in stats:
            evidence.append((evidence_stamp(row, "stats"), 2, "stats", row))
        evidence.sort(key=lambda item: (item[0], item[1], json.dumps(item[3], ensure_ascii=False, sort_keys=True)))
        stamped = [item for item in evidence if item[0]]
        latest = stamped[-1] if stamped else ("", 0, "", {})
        latest_row = latest[3]

        roster_stamps = [evidence_stamp(row, "roster") for row in roster if evidence_stamp(row, "roster")]
        stats_stamps = [evidence_stamp(row, "stats") for row in stats if evidence_stamp(row, "stats")]
        all_stamps = roster_stamps + stats_stamps
        latest_roster_stamp = max(roster_stamps) if roster_stamps else ""
        latest_roster_rows = [row for row in roster if latest_roster_stamp and evidence_stamp(row, "roster") == latest_roster_stamp]
        latest_team_pairs = sorted({
            (sval(row, "team_id"), sval(row, "team_name"))
            for row in latest_roster_rows if sval(row, "team_id")
        })

        latest_roster_meta = {}
        if roster:
            latest_roster_meta = sorted(
                roster,
                key=lambda row: (
                    evidence_stamp(row, "roster"),
                    sval(row, "team_id"),
                    json.dumps(row, ensure_ascii=False, sort_keys=True),
                ),
            )[-1]

        name = sval(latest_row, "player_name")
        position = sval(latest_row, "position") or sval(latest_roster_meta, "position")
        if not name:
            candidates = [sval(row, "player_name") for row in roster + stats if sval(row, "player_name")]
            name = candidates[-1] if candidates else ""

        output.append({
            "player_id": player_id,
            "latest_observed_name": name,
            "latest_observed_position": position,
            "latest_observed_age": sval(latest_roster_meta, "age"),
            "latest_observed_number": sval(latest_roster_meta, "number"),
            "latest_observed_photo_url": sval(latest_roster_meta, "photo_url"),
            "first_seen_at_utc": min(all_stamps) if all_stamps else "",
            "last_seen_at_utc": max(all_stamps) if all_stamps else "",
            "latest_roster_seen_at_utc": latest_roster_stamp,
            "latest_stats_seen_at_utc": max(stats_stamps) if stats_stamps else "",
            "roster_observation_rows": str(len(roster)),
            "roster_team_count": str(len({sval(row, "team_id") for row in roster if sval(row, "team_id")})),
            "latest_roster_team_ids": ",".join(pair[0] for pair in latest_team_pairs),
            "latest_roster_team_names": " | ".join(pair[1] for pair in latest_team_pairs if pair[1]),
            "stats_fixture_count": str(len({sval(row, "fixture_id") for row in stats if sval(row, "fixture_id")})),
            "stats_row_count": str(len(stats)),
            "has_roster_evidence": "YES" if roster else "NO",
            "has_match_stats_evidence": "YES" if stats else "NO",
            "evidence_sources": ",".join(source for source, rows in (("roster_history", roster), ("player_stats", stats)) if rows),
            "source": "stage80:roster_history+player_stats",
            "projection_version": VERSION,
        })
    return output, invalid_roster, invalid_stats


def main():
    roster_present = ROSTERS.exists()
    stats_present = STATS.exists()
    roster_rows = read_csv(ROSTERS)
    stats_rows = read_snapshot_rows(STATS)
    catalog, invalid_roster, invalid_stats = build_catalog(roster_rows, stats_rows)
    write_csv_atomic(CATALOG, catalog)
    invalid = invalid_roster + invalid_stats
    if invalid:
        status = "ATTENTION"
    elif not roster_present and not stats_present:
        status = "WAITING_SOURCE"
    else:
        status = "OK"
    meta = {
        "version": VERSION,
        "run_at_utc": iso_now(),
        "status": status,
        "roster_history_present": roster_present,
        "player_stats_present": stats_present,
        "roster_source_rows": len(roster_rows),
        "stats_source_rows": len(stats_rows),
        "catalog_players": len(catalog),
        "players_with_roster_evidence": sum(1 for row in catalog if row["has_roster_evidence"] == "YES"),
        "players_with_match_stats_evidence": sum(1 for row in catalog if row["has_match_stats_evidence"] == "YES"),
        "invalid_roster_rows": invalid_roster,
        "invalid_stats_rows": invalid_stats,
        "provider_calls": 0,
        "derived_projection": True,
        "source_of_truth": False,
        "transfer_dates_inferred": False,
        "current_team_inferred": False,
        "xg_xa_fabricated": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    if invalid:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
