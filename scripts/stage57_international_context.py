#!/usr/bin/env python3
"""Stage 57: FIFA international-window proximity context for PBK forward signals.

This is deliberately a calendar-level context layer. It does NOT infer that a
club player was called up, travelled, or played for a national team from the
player's nationality. Player-level international participation remains
UNVERIFIED until a future source provides direct evidence.

Calendar references frozen for the 2026/27 club season:
- FIFA men's IMC: 21 Sep-6 Oct 2026 (max 4), 9-17 Nov 2026 (max 2)
- 2026/27 season March window: 22-30 Mar 2027 (max 2)
- UEFA Nations League league phase: 24 Sep-6 Oct and 12-17 Nov 2026

All outputs are context-only and cannot alter R1/R2/R3 eligibility.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
CONTEXT = OPS / "context_latest.csv"
OUT = OPS / "international_context.csv"
META = OPS / "stage57_last_run.json"

FIELDS = [
    "forward_id","rule","api_fixture_id","home_team","away_team","kickoff_utc",
    "fifa_relation","fifa_window_name","fifa_window_start_utc","fifa_window_end_utc","fifa_max_matches",
    "hours_to_fifa_window_start","hours_since_fifa_window_end","within_7d_before_fifa_window","within_7d_after_fifa_window",
    "uefa_nations_league_relation","uefa_window_start_utc","uefa_window_end_utc",
    "player_level_international_status","player_level_reason","context_only","notes"
]


def dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso(x):
    return x.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


FIFA_WINDOWS = [
    {
        "name": "FIFA 2026 combined Sep-Oct window",
        "start": dt("2026-09-21T00:00:00Z"),
        "end": dt("2026-10-06T23:59:59Z"),
        "max_matches": 4,
    },
    {
        "name": "FIFA 2026 November window",
        "start": dt("2026-11-09T00:00:00Z"),
        "end": dt("2026-11-17T23:59:59Z"),
        "max_matches": 2,
    },
    {
        "name": "FIFA 2027 March window",
        "start": dt("2027-03-22T00:00:00Z"),
        "end": dt("2027-03-30T23:59:59Z"),
        "max_matches": 2,
    },
]

UEFA_NL_WINDOWS = [
    (dt("2026-09-24T00:00:00Z"), dt("2026-10-06T23:59:59Z")),
    (dt("2026-11-12T00:00:00Z"), dt("2026-11-17T23:59:59Z")),
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


def latest_by(rows):
    out = {}
    for r in rows:
        fid = r.get("forward_id") or ""
        if not fid:
            continue
        cur = out.get(fid)
        if cur is None or (r.get("captured_at_utc") or "") > (cur.get("captured_at_utc") or ""):
            out[fid] = r
    return out


def parse_kickoff(bet, ctx):
    raw = ctx.get("current_kickoff_utc") or ""
    if raw:
        try:
            return dt(raw)
        except Exception:
            pass
    date = bet.get("match_date") or ""
    tm = bet.get("kickoff_time") or ""
    if date and tm:
        try:
            return dt(f"{date}T{tm}:00Z")
        except Exception:
            return None
    return None


def relation_to_window(kickoff, start, end):
    if start <= kickoff <= end:
        return "INSIDE", None, None
    if kickoff < start:
        return "BEFORE", (start - kickoff).total_seconds() / 3600.0, None
    return "AFTER", None, (kickoff - end).total_seconds() / 3600.0


def nearest_fifa_window(kickoff):
    scored = []
    for w in FIFA_WINDOWS:
        rel, to_start, since_end = relation_to_window(kickoff, w["start"], w["end"])
        if rel == "INSIDE":
            distance = 0.0
        elif rel == "BEFORE":
            distance = to_start
        else:
            distance = since_end
        scored.append((distance, w, rel, to_start, since_end))
    return min(scored, key=lambda x: x[0])


def nearest_uefa_window(kickoff):
    scored = []
    for start, end in UEFA_NL_WINDOWS:
        rel, to_start, since_end = relation_to_window(kickoff, start, end)
        distance = 0.0 if rel == "INSIDE" else (to_start if to_start is not None else since_end)
        scored.append((distance, start, end, rel))
    return min(scored, key=lambda x: x[0])


def main():
    forward = [r for r in read_csv(FORWARD) if r.get("status") in {"PAPER", "OPEN", "REVIEW"}]
    ctx = latest_by(read_csv(CONTEXT))
    rows = []

    for bet in forward:
        fid = bet.get("forward_id") or ""
        c = ctx.get(fid, {})
        kickoff = parse_kickoff(bet, c)
        if not kickoff:
            continue

        _, fw, frel, to_start, since_end = nearest_fifa_window(kickoff)
        _, ustart, uend, urel = nearest_uefa_window(kickoff)
        before7 = to_start is not None and 0 <= to_start <= 7 * 24
        after7 = since_end is not None and 0 <= since_end <= 7 * 24
        notes = []
        if before7:
            notes.append("club match within 7 days before FIFA release window")
        if after7:
            notes.append("club match within 7 days after FIFA international window")
        if frel == "INSIDE":
            notes.append("club fixture falls inside FIFA international window; verify scheduling/status")

        rows.append({
            "forward_id": fid,
            "rule": bet.get("rule") or "",
            "api_fixture_id": bet.get("api_fixture_id") or "",
            "home_team": c.get("home_team") or bet.get("home_team") or "",
            "away_team": c.get("away_team") or bet.get("away_team") or "",
            "kickoff_utc": iso(kickoff),
            "fifa_relation": frel,
            "fifa_window_name": fw["name"],
            "fifa_window_start_utc": iso(fw["start"]),
            "fifa_window_end_utc": iso(fw["end"]),
            "fifa_max_matches": fw["max_matches"],
            "hours_to_fifa_window_start": "" if to_start is None else f"{to_start:.1f}",
            "hours_since_fifa_window_end": "" if since_end is None else f"{since_end:.1f}",
            "within_7d_before_fifa_window": "YES" if before7 else "NO",
            "within_7d_after_fifa_window": "YES" if after7 else "NO",
            "uefa_nations_league_relation": urel,
            "uefa_window_start_utc": iso(ustart),
            "uefa_window_end_utc": iso(uend),
            "player_level_international_status": "UNVERIFIED",
            "player_level_reason": "Nationality is not evidence of call-up, travel, or appearance",
            "context_only": "YES",
            "notes": "; ".join(notes),
        })

    write_csv(OUT, FIELDS, rows)
    meta = {
        "run_at_utc": iso(datetime.now(timezone.utc)),
        "status": "OK",
        "active_forward_rows": len(forward),
        "international_context_rows": len(rows),
        "policy": {
            "role": "calendar context only; never changes strategy eligibility",
            "player_level": "UNVERIFIED unless direct call-up/appearance evidence is added later",
            "nationality": "never treated as evidence of national-team participation",
            "fifa_windows": [
                {"name": w["name"], "start": iso(w["start"]), "end": iso(w["end"]), "max_matches": w["max_matches"]}
                for w in FIFA_WINDOWS
            ],
        },
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
