#!/usr/bin/env python3
"""PBK #270 — match-specific prematch venue state rail.

Builds one deterministic venue-state row per active forward fixture.

Static venue facts come from the canonical Stage265 registry.
Dynamic roof state is accepted only from explicit fixture evidence captured
strictly before kickoff. Retractable-roof venues with no prematch evidence
remain PREMATCH_REQUIRED / NOT_CAPTURED.

No network/provider calls. No predictive/betting/value/stake authority.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
ROOT = Path(__file__).resolve().parents[1]

FORWARD = OPS / "forward_log.csv"
CONTEXT = OPS / "context_latest.csv"
VENUES = OPS / "pbk16_venue_registry.csv"
EVIDENCE = ROOT / "config" / "pbk_fixture_venue_state_evidence.csv"

OUTPUT = OPS / "prematch_venue_state.csv"
META = OPS / "stage270_prematch_venue_state_last_run.json"

VERSION = "PBK_PREMATCH_VENUE_STATE_V1"
ACTIVE = {"PAPER", "OPEN", "REVIEW"}
ROOF_STATES = {"OPEN", "CLOSED", "PARTIAL", "UNKNOWN"}

FIELDS = [
    "forward_id","rule","api_fixture_id","kickoff_utc",
    "home_team_id","home_team","away_team",
    "venue_id","venue_name","roof_type",
    "roof_state_requirement","roof_state_actual",
    "roof_state_capture_status",
    "evidence_captured_at_utc","evidence_source",
    "evidence_time_status","usable_for_prematch",
    "weather_exposure_resolution",
    "context_only","predictive_authority","betting_authority",
    "projection_version",
]


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    temp.replace(path)


def parse_iso(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def latest_by(rows, key):
    out = {}
    for row in rows:
        k = str(row.get(key) or "").strip()
        if not k:
            continue
        cur = out.get(k)
        if cur is None or str(row.get("captured_at_utc") or "") > str(cur.get("captured_at_utc") or ""):
            out[k] = row
    return out


def venue_by_team(rows):
    out = {}
    for row in rows:
        team_id = str(row.get("team_id") or "").strip()
        if team_id:
            out[team_id] = row
    return out


def prematch_evidence_by_fixture(rows):
    out = {}
    for row in rows:
        fixture_id = str(row.get("api_fixture_id") or "").strip()
        if not fixture_id:
            continue
        state = str(row.get("roof_state_actual") or "").strip().upper()
        if state not in ROOF_STATES:
            continue
        captured = parse_iso(row.get("captured_at_utc"))
        kickoff = parse_iso(row.get("kickoff_utc"))
        if not captured or not kickoff or captured >= kickoff:
            continue
        cur = out.get(fixture_id)
        if cur is None or captured > parse_iso(cur.get("captured_at_utc")):
            out[fixture_id] = row
    return out


def roof_requirement(roof_type):
    roof_type = str(roof_type or "").strip()
    if roof_type == "RETRACTABLE_FULL_PITCH_COVER":
        return "PREMATCH_REQUIRED"
    if roof_type in {"ALL_SEATS_COVERED_OPEN_PITCH", "ALL_STANDS_COVERED_OPEN_PITCH", "LIMITED_STAND_COVER", "PARTIAL_STAND_COVER"}:
        return "STATIC_OPEN_PITCH"
    if roof_type in {"UNKNOWN", ""}:
        return "UNKNOWN"
    return "STATIC"


def weather_exposure_resolution(roof_type, requirement, actual):
    if requirement == "PREMATCH_REQUIRED":
        if actual == "CLOSED":
            return "ROOF_CLOSED_WEATHER_SHIELDED"
        if actual in {"OPEN", "PARTIAL"}:
            return "ROOF_OPEN_OR_PARTIAL_WEATHER_EXPOSED"
        return "UNRESOLVED_RETRACTABLE_ROOF_STATE"
    if roof_type in {"ALL_SEATS_COVERED_OPEN_PITCH", "ALL_STANDS_COVERED_OPEN_PITCH", "LIMITED_STAND_COVER", "PARTIAL_STAND_COVER"}:
        return "OPEN_PITCH_WEATHER_EXPOSED"
    if roof_type in {"", "UNKNOWN"}:
        return "UNKNOWN"
    return "STATIC_VENUE_CONTEXT"


def build_rows(forward, context, venues, evidence):
    ctx = latest_by(context, "forward_id")
    by_team = venue_by_team(venues)
    by_fixture = prematch_evidence_by_fixture(evidence)

    result = []

    for bet in forward:
        if str(bet.get("status") or "") not in ACTIVE:
            continue

        fid = str(bet.get("forward_id") or "").strip()
        c = ctx.get(fid, {})

        fixture_id = str(bet.get("api_fixture_id") or "").strip()
        home_team_id = str(c.get("home_team_id") or "").strip()

        venue = by_team.get(home_team_id, {})
        roof_type = str(venue.get("roof_type") or "UNKNOWN").strip() or "UNKNOWN"
        requirement = roof_requirement(roof_type)

        ev = by_fixture.get(fixture_id, {})
        actual = str(ev.get("roof_state_actual") or "").strip().upper()
        if actual not in ROOF_STATES:
            actual = "UNKNOWN"

        kickoff = str(c.get("current_kickoff_utc") or ev.get("kickoff_utc") or "").strip()

        if ev:
            time_status = "PREMATCH_FROZEN"
            usable = "true"
            capture_status = "CAPTURED"
        elif requirement == "PREMATCH_REQUIRED":
            time_status = "UNKNOWN"
            usable = "false"
            capture_status = "NOT_CAPTURED"
        else:
            time_status = "STATIC_CONTEXT"
            usable = "true"
            capture_status = "NOT_REQUIRED"

        result.append({
            "forward_id": fid,
            "rule": bet.get("rule") or "",
            "api_fixture_id": fixture_id,
            "kickoff_utc": kickoff,
            "home_team_id": home_team_id,
            "home_team": c.get("home_team") or bet.get("home_team") or "",
            "away_team": c.get("away_team") or bet.get("away_team") or "",
            "venue_id": venue.get("venue_id") or "",
            "venue_name": venue.get("venue_name") or c.get("venue_name") or "",
            "roof_type": roof_type,
            "roof_state_requirement": requirement,
            "roof_state_actual": actual,
            "roof_state_capture_status": capture_status,
            "evidence_captured_at_utc": ev.get("captured_at_utc") or "",
            "evidence_source": ev.get("source") or "",
            "evidence_time_status": time_status,
            "usable_for_prematch": usable,
            "weather_exposure_resolution": weather_exposure_resolution(
                roof_type, requirement, actual
            ),
            "context_only": "YES",
            "predictive_authority": "NOT_AUTHORIZED",
            "betting_authority": "NOT_AUTHORIZED",
            "projection_version": VERSION,
        })

    result.sort(key=lambda r: (r["kickoff_utc"], r["forward_id"]))
    return result


def main():
    rows = build_rows(
        read_csv(FORWARD),
        read_csv(CONTEXT),
        read_csv(VENUES),
        read_csv(EVIDENCE),
    )
    write_csv(OUTPUT, rows)

    retractable = [r for r in rows if r["roof_state_requirement"] == "PREMATCH_REQUIRED"]
    unresolved = [r for r in retractable if r["roof_state_capture_status"] != "CAPTURED"]

    meta = {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "OK",
        "active_fixture_rows": len(rows),
        "retractable_roof_rows": len(retractable),
        "unresolved_retractable_roof_rows": len(unresolved),
        "provider_calls": 0,
        "web_calls": 0,
        "postkickoff_evidence_accepted": 0,
        "policy": {
            "dynamic_roof_state": "accepted only from explicit evidence captured strictly before kickoff",
            "missing_retractable_state": "PREMATCH_REQUIRED / NOT_CAPTURED; never inferred",
            "static_roof_capability": "from canonical Stage265 registry",
            "authority": "context only; no predictive/betting/value/stake authority",
        },
    }

    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
