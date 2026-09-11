#!/usr/bin/env python3
"""Rebuild Stage 56 compact latest view without collapsing numeric zero to blank."""
from __future__ import annotations

import csv
import os
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
CONTEXT = OPS / "context_latest.csv"
WEATHER = OPS / "weather_snapshots.csv"
ROTATION = OPS / "rotation_snapshots.csv"
LATEST = OPS / "stage56_latest.csv"

FIELDS = [
    "forward_id","rule","api_fixture_id","home_team","away_team","kickoff_utc",
    "weather_snapshot_type","weather_captured_at_utc","temperature_c","precipitation_probability_pct",
    "precipitation_mm","wind_speed_10m_kmh","wind_gusts_10m_kmh","visibility_m","weather_code",
    "rotation_captured_at_utc","home_retained_starters","away_retained_starters","home_changed_starters",
    "away_changed_starters","home_retained_pct","away_retained_pct","rotation_verified","context_only"
]


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def latest_by(rows, key="forward_id"):
    out = {}
    for r in rows:
        k = r.get(key) or ""
        if not k:
            continue
        cur = out.get(k)
        if cur is None or (r.get("captured_at_utc") or "") > (cur.get("captured_at_utc") or ""):
            out[k] = r
    return out


def val(row, key):
    value = row.get(key)
    return "" if value is None else value


def main():
    active = [r for r in read_csv(FORWARD) if r.get("status") in {"PAPER", "OPEN", "REVIEW"}]
    ctx = latest_by(read_csv(CONTEXT))
    weather = latest_by(read_csv(WEATHER))
    rotation = latest_by(read_csv(ROTATION))

    rows = []
    for bet in active:
        fid = bet.get("forward_id") or ""
        c, w, r = ctx.get(fid, {}), weather.get(fid, {}), rotation.get(fid, {})
        rows.append({
            "forward_id": fid,
            "rule": val(bet, "rule"),
            "api_fixture_id": val(bet, "api_fixture_id"),
            "home_team": val(c, "home_team") or val(bet, "home_team"),
            "away_team": val(c, "away_team") or val(bet, "away_team"),
            "kickoff_utc": val(c, "current_kickoff_utc") or val(w, "kickoff_utc"),
            "weather_snapshot_type": val(w, "snapshot_type"),
            "weather_captured_at_utc": val(w, "captured_at_utc"),
            "temperature_c": val(w, "temperature_c"),
            "precipitation_probability_pct": val(w, "precipitation_probability_pct"),
            "precipitation_mm": val(w, "precipitation_mm"),
            "wind_speed_10m_kmh": val(w, "wind_speed_10m_kmh"),
            "wind_gusts_10m_kmh": val(w, "wind_gusts_10m_kmh"),
            "visibility_m": val(w, "visibility_m"),
            "weather_code": val(w, "weather_code"),
            "rotation_captured_at_utc": val(r, "captured_at_utc"),
            "home_retained_starters": val(r, "home_retained_starters"),
            "away_retained_starters": val(r, "away_retained_starters"),
            "home_changed_starters": val(r, "home_changed_starters"),
            "away_changed_starters": val(r, "away_changed_starters"),
            "home_retained_pct": val(r, "home_retained_pct"),
            "away_retained_pct": val(r, "away_retained_pct"),
            "rotation_verified": "YES" if r.get("home_rotation_verified") == "YES" and r.get("away_rotation_verified") == "YES" else "NO",
            "context_only": "YES",
        })
    write_csv(LATEST, FIELDS, rows)
    print(f"stage56_latest_rows={len(rows)}")


if __name__ == "__main__":
    main()
