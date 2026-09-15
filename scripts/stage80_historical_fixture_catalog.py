#!/usr/bin/env python3
"""Stage80 — normalized historical fixture catalog.

This provider-free projection compacts append-only fixture observations into one
reproducible row per fixture. `fixture_history_snapshots.csv` remains the evidence
source of truth; this catalog is only a convenient normalized warehouse layer.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
HISTORY = OPS / "fixture_history_snapshots.csv"
CATALOG = OPS / "historical_fixtures.csv"
META = OPS / "stage80_fixture_catalog_last_run.json"
VERSION = "PBK_STAGE80_HISTORICAL_FIXTURE_CATALOG_V1"
TERMINAL = {"FINISHED", "FT", "AET", "PEN"}

FIELDS = [
    "fixture_id", "provider_league_id", "league_name", "country", "season", "round",
    "home_team", "away_team", "first_kickoff_utc", "latest_kickoff_utc",
    "reschedule_observed", "first_seen_at_utc", "last_seen_at_utc",
    "observation_count", "latest_status", "latest_source_status",
    "terminal_observed", "terminal_observed_at_utc", "final_score_home",
    "final_score_away", "source", "projection_version",
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


def is_terminal(row):
    return sval(row, "source_status").upper() in TERMINAL or sval(row, "status").upper() in TERMINAL


def valid_observation(row):
    return bool(sval(row, "fixture_id") and sval(row, "observed_at_utc"))


def build_catalog(rows):
    grouped = defaultdict(list)
    invalid = 0
    for row in rows:
        if not valid_observation(row):
            invalid += 1
            continue
        grouped[sval(row, "fixture_id")].append(dict(row))

    output = []
    for fixture_id in sorted(grouped, key=lambda x: (len(x), x)):
        observations = sorted(grouped[fixture_id], key=lambda row: sval(row, "observed_at_utc"))
        first = observations[0]
        latest = observations[-1]
        kickoffs = [sval(row, "kickoff_utc") for row in observations if sval(row, "kickoff_utc")]
        distinct_kickoffs = list(dict.fromkeys(kickoffs))
        terminals = [row for row in observations if is_terminal(row)]
        terminal = terminals[-1] if terminals else None
        output.append({
            "fixture_id": fixture_id,
            "provider_league_id": sval(latest, "provider_league_id") or sval(first, "provider_league_id"),
            "league_name": latest.get("league_name") or first.get("league_name") or "",
            "country": latest.get("country") or first.get("country") or "",
            "season": latest.get("season") or first.get("season") or "",
            "round": latest.get("round") or first.get("round") or "",
            "home_team": latest.get("home_team") or first.get("home_team") or "",
            "away_team": latest.get("away_team") or first.get("away_team") or "",
            "first_kickoff_utc": distinct_kickoffs[0] if distinct_kickoffs else "",
            "latest_kickoff_utc": distinct_kickoffs[-1] if distinct_kickoffs else "",
            "reschedule_observed": "YES" if len(set(distinct_kickoffs)) > 1 else "NO",
            "first_seen_at_utc": sval(first, "observed_at_utc"),
            "last_seen_at_utc": sval(latest, "observed_at_utc"),
            "observation_count": str(len(observations)),
            "latest_status": sval(latest, "status"),
            "latest_source_status": sval(latest, "source_status"),
            "terminal_observed": "YES" if terminal else "NO",
            "terminal_observed_at_utc": sval(terminal, "observed_at_utc") if terminal else "",
            "final_score_home": sval(terminal, "score_home") if terminal else "",
            "final_score_away": sval(terminal, "score_away") if terminal else "",
            "source": "stage80:fixture_history_snapshots",
            "projection_version": VERSION,
        })
    return output, invalid


def main():
    source_present = HISTORY.exists()
    source_rows = read_csv(HISTORY)
    catalog, invalid = build_catalog(source_rows)
    write_csv_atomic(CATALOG, catalog)
    status = "WAITING_SOURCE" if not source_present else ("ATTENTION" if invalid else "OK")
    meta = {
        "version": VERSION,
        "run_at_utc": iso_now(),
        "status": status,
        "source_present": source_present,
        "source_observations": len(source_rows),
        "catalog_fixtures": len(catalog),
        "terminal_fixtures": sum(1 for row in catalog if row["terminal_observed"] == "YES"),
        "rescheduled_fixtures": sum(1 for row in catalog if row["reschedule_observed"] == "YES"),
        "invalid_source_rows": invalid,
        "provider_calls": 0,
        "derived_projection": True,
        "source_of_truth": False,
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
