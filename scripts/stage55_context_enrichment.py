#!/usr/bin/env python3
"""Stage 55 v1: timestamped live context enrichment for canonical forward signals.

Purpose
-------
Add explanatory pre-match context without changing R1/R2/R3 eligibility.
Snapshots are append-only by (forward_id, snapshot_type):
  BASELINE  - first operational context capture after a signal enters forward
  T24       - first capture between 30h and 6h before current kickoff
  T3        - first capture between 6h and 90m before current kickoff
  T60       - first capture <=90m before kickoff *only when official lineups exist*

Context collected from API-Football:
  * current fixture identity/status, referee, venue
  * previous and next club fixture for each team across ALL competitions
  * domestic cup / UEFA calendar adjacency classification (context only)
  * injuries near T24/T3/T60
  * official starting XI when published near kickoff

No context field is allowed to alter the frozen trigger or canonical strategy flags.
"""
from __future__ import annotations

import csv
import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://v3.football.api-sports.io"
OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
SNAPSHOTS = OPS / "match_context_snapshots.csv"
LATEST = OPS / "context_latest.csv"
META = OPS / "stage55_last_run.json"

FIELDS = [
    "forward_id", "rule", "api_fixture_id", "snapshot_type", "captured_at_utc",
    "current_kickoff_utc", "hours_to_kickoff", "fixture_status",
    "league", "home_team", "away_team", "home_team_id", "away_team_id",
    "referee", "venue_name", "venue_city",
    "home_prev_fixture_id", "home_prev_date_utc", "home_prev_opponent", "home_prev_competition", "home_prev_comp_class",
    "away_prev_fixture_id", "away_prev_date_utc", "away_prev_opponent", "away_prev_competition", "away_prev_comp_class",
    "home_next_fixture_id", "home_next_date_utc", "home_next_opponent", "home_next_competition", "home_next_comp_class",
    "away_next_fixture_id", "away_next_date_utc", "away_next_opponent", "away_next_competition", "away_next_comp_class",
    "home_rest_hours", "away_rest_hours", "home_hours_to_next", "away_hours_to_next",
    "home_prev_is_uefa_or_cup", "away_prev_is_uefa_or_cup", "home_next_is_uefa_or_cup", "away_next_is_uefa_or_cup",
    "injuries_count", "home_injuries_count", "away_injuries_count", "injuries_json",
    "lineups_available", "home_formation", "away_formation", "home_coach", "away_coach",
    "home_start_xi_json", "away_start_xi_json",
    "context_only", "notes"
]


def fnum(x):
    try:
        v = float(str(x).strip())
        return v if math.isfinite(v) else None
    except Exception:
        return None


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if dt else ""


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def read_csv(path):
    if not path.exists():
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames or [])


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def api_get(path, params=None, attempts=3):
    key = os.getenv("API_FOOTBALL_KEY", "").strip()
    if not key:
        raise RuntimeError("API_FOOTBALL_KEY is missing")
    qs = urllib.parse.urlencode(params or {})
    url = API_BASE + path + ("?" + qs if qs else "")
    last = None
    for n in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"x-apisports-key": key, "User-Agent": "football-data-bridge/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
            if data.get("errors"):
                raise RuntimeError(f"API-Football {path}: {data['errors']}")
            return data
        except Exception as exc:
            last = exc
            if n < attempts:
                time.sleep(n * 3)
    raise last


def comp_class(league_obj):
    name = str((league_obj or {}).get("name") or "")
    country = str((league_obj or {}).get("country") or "")
    low = name.lower()
    uefa_terms = ("champions league", "europa league", "conference league", "uefa")
    cup_terms = (
        "cup", "copa del rey", "coppa italia", "dfb-pokal", "pokal", "coupe de france",
        "fa cup", "efl", "carabao", "super cup", "supercup", "community shield", "trophy"
    )
    if any(t in low for t in uefa_terms):
        return "UEFA"
    if any(t in low for t in cup_terms):
        return "DOMESTIC_CUP" if country and country.lower() not in {"world", "europe"} else "CUP_OTHER"
    return "LEAGUE_OR_OTHER"


def fixture_brief(x, team_id, target_dt):
    if not x:
        return {}
    fx = x.get("fixture", {}) or {}
    teams = x.get("teams", {}) or {}
    league = x.get("league", {}) or {}
    dt = parse_iso(fx.get("date"))
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}
    opp = away.get("name") if int(home.get("id") or 0) == int(team_id or 0) else home.get("name")
    return {
        "id": fx.get("id") or "",
        "dt": dt,
        "opponent": opp or "",
        "competition": league.get("name") or "",
        "class": comp_class(league),
        "delta_hours": ((dt - target_dt).total_seconds() / 3600.0) if dt and target_dt else None,
    }


def surrounding_fixture(team_id, target_fixture_id, target_dt, direction):
    param = "last" if direction == "prev" else "next"
    d = api_get("/fixtures", {"team": team_id, param: 8, "timezone": "UTC"})
    candidates = []
    for x in d.get("response", []) or []:
        fx = x.get("fixture", {}) or {}
        fid = str(fx.get("id") or "")
        if fid == str(target_fixture_id):
            continue
        dt = parse_iso(fx.get("date"))
        if not dt:
            continue
        if direction == "prev" and dt < target_dt:
            candidates.append((dt, x))
        elif direction == "next" and dt > target_dt:
            candidates.append((dt, x))
    if not candidates:
        return {}
    chosen = max(candidates, key=lambda z: z[0])[1] if direction == "prev" else min(candidates, key=lambda z: z[0])[1]
    return fixture_brief(chosen, team_id, target_dt)


def get_fixture(fixture_id):
    d = api_get("/fixtures", {"id": fixture_id, "timezone": "UTC"})
    return (d.get("response") or [None])[0]


def get_injuries(fixture_id):
    try:
        d = api_get("/injuries", {"fixture": fixture_id})
    except Exception as exc:
        return [], f"injuries unavailable: {exc}"
    out = []
    for x in d.get("response", []) or []:
        p = x.get("player", {}) or {}
        t = x.get("team", {}) or {}
        out.append({
            "player_id": p.get("id"), "player": p.get("name"), "team_id": t.get("id"), "team": t.get("name"),
            "type": p.get("type"), "reason": p.get("reason")
        })
    return out, ""


def get_lineups(fixture_id):
    try:
        d = api_get("/fixtures/lineups", {"fixture": fixture_id})
    except Exception as exc:
        return [], f"lineups unavailable: {exc}"
    return d.get("response", []) or [], ""


def lineup_for_team(lineups, team_id):
    for x in lineups:
        team = x.get("team", {}) or {}
        if int(team.get("id") or 0) != int(team_id or 0):
            continue
        xi = []
        for z in x.get("startXI", []) or []:
            p = z.get("player", {}) or {}
            xi.append({"id": p.get("id"), "name": p.get("name"), "number": p.get("number"), "pos": p.get("pos"), "grid": p.get("grid")})
        coach = (x.get("coach", {}) or {}).get("name") or ""
        return {"formation": x.get("formation") or "", "coach": coach, "xi": xi}
    return {"formation": "", "coach": "", "xi": []}


def select_due_type(done, forward_id, hours):
    if (forward_id, "BASELINE") not in done:
        return "BASELINE"
    if 6.0 < hours <= 30.0 and (forward_id, "T24") not in done:
        return "T24"
    if 1.5 < hours <= 6.0 and (forward_id, "T3") not in done:
        return "T3"
    if 0.0 < hours <= 1.5 and (forward_id, "T60") not in done:
        return "T60"
    return ""


def main():
    now = now_utc()
    forward, _ = read_csv(FORWARD)
    snapshots, _ = read_csv(SNAPSHOTS)
    done = {(r.get("forward_id"), r.get("snapshot_type")) for r in snapshots}
    active = [r for r in forward if r.get("status") in {"PAPER", "OPEN", "REVIEW"}]
    new_rows = []
    fixture_checks = 0
    injury_calls = 0
    lineup_calls = 0
    schedule_calls = 0
    warnings = []

    for bet in active:
        forward_id = bet.get("forward_id") or ""
        fixture_id = bet.get("api_fixture_id") or ""
        if not fixture_id:
            continue
        try:
            x = get_fixture(fixture_id)
            fixture_checks += 1
        except Exception as exc:
            warnings.append(f"fixture {fixture_id}: {exc}")
            continue
        if not x:
            warnings.append(f"fixture {fixture_id}: empty response")
            continue

        fx = x.get("fixture", {}) or {}
        teams = x.get("teams", {}) or {}
        league = x.get("league", {}) or {}
        home = teams.get("home", {}) or {}
        away = teams.get("away", {}) or {}
        target_dt = parse_iso(fx.get("date"))
        if not target_dt:
            continue
        hours = (target_dt - now).total_seconds() / 3600.0
        snapshot_type = select_due_type(done, forward_id, hours)
        if not snapshot_type:
            continue

        home_id, away_id = home.get("id"), away.get("id")
        try:
            hp = surrounding_fixture(home_id, fixture_id, target_dt, "prev"); schedule_calls += 1
            hn = surrounding_fixture(home_id, fixture_id, target_dt, "next"); schedule_calls += 1
            ap = surrounding_fixture(away_id, fixture_id, target_dt, "prev"); schedule_calls += 1
            an = surrounding_fixture(away_id, fixture_id, target_dt, "next"); schedule_calls += 1
        except Exception as exc:
            warnings.append(f"schedule {fixture_id}: {exc}")
            hp = hn = ap = an = {}

        injuries = []
        injury_note = ""
        if snapshot_type in {"T24", "T3", "T60"}:
            injuries, injury_note = get_injuries(fixture_id)
            injury_calls += 1

        lineups = []
        lineup_note = ""
        if snapshot_type == "T60":
            lineups, lineup_note = get_lineups(fixture_id)
            lineup_calls += 1
            # Do not freeze T60 until official lineups are actually present.
            if not lineups:
                if lineup_note:
                    warnings.append(f"lineup {fixture_id}: {lineup_note}")
                continue

        hl = lineup_for_team(lineups, home_id)
        al = lineup_for_team(lineups, away_id)
        h_inj = [z for z in injuries if int(z.get("team_id") or 0) == int(home_id or 0)]
        a_inj = [z for z in injuries if int(z.get("team_id") or 0) == int(away_id or 0)]
        notes = "; ".join(z for z in (injury_note, lineup_note) if z)

        def gap_prev(b):
            d = b.get("dt") if b else None
            return (target_dt - d).total_seconds() / 3600.0 if d else None

        def gap_next(b):
            d = b.get("dt") if b else None
            return (d - target_dt).total_seconds() / 3600.0 if d else None

        row = {
            "forward_id": forward_id, "rule": bet.get("rule"), "api_fixture_id": fixture_id,
            "snapshot_type": snapshot_type, "captured_at_utc": iso(now), "current_kickoff_utc": iso(target_dt),
            "hours_to_kickoff": f"{hours:.2f}", "fixture_status": ((fx.get("status", {}) or {}).get("short") or ""),
            "league": league.get("name") or bet.get("league") or "", "home_team": home.get("name") or bet.get("home_team") or "",
            "away_team": away.get("name") or bet.get("away_team") or "", "home_team_id": home_id or "", "away_team_id": away_id or "",
            "referee": fx.get("referee") or "", "venue_name": ((fx.get("venue", {}) or {}).get("name") or ""),
            "venue_city": ((fx.get("venue", {}) or {}).get("city") or ""),
            "home_prev_fixture_id": hp.get("id", ""), "home_prev_date_utc": iso(hp.get("dt")), "home_prev_opponent": hp.get("opponent", ""),
            "home_prev_competition": hp.get("competition", ""), "home_prev_comp_class": hp.get("class", ""),
            "away_prev_fixture_id": ap.get("id", ""), "away_prev_date_utc": iso(ap.get("dt")), "away_prev_opponent": ap.get("opponent", ""),
            "away_prev_competition": ap.get("competition", ""), "away_prev_comp_class": ap.get("class", ""),
            "home_next_fixture_id": hn.get("id", ""), "home_next_date_utc": iso(hn.get("dt")), "home_next_opponent": hn.get("opponent", ""),
            "home_next_competition": hn.get("competition", ""), "home_next_comp_class": hn.get("class", ""),
            "away_next_fixture_id": an.get("id", ""), "away_next_date_utc": iso(an.get("dt")), "away_next_opponent": an.get("opponent", ""),
            "away_next_competition": an.get("competition", ""), "away_next_comp_class": an.get("class", ""),
            "home_rest_hours": "" if gap_prev(hp) is None else f"{gap_prev(hp):.1f}",
            "away_rest_hours": "" if gap_prev(ap) is None else f"{gap_prev(ap):.1f}",
            "home_hours_to_next": "" if gap_next(hn) is None else f"{gap_next(hn):.1f}",
            "away_hours_to_next": "" if gap_next(an) is None else f"{gap_next(an):.1f}",
            "home_prev_is_uefa_or_cup": "YES" if hp.get("class") in {"UEFA", "DOMESTIC_CUP", "CUP_OTHER"} else "NO",
            "away_prev_is_uefa_or_cup": "YES" if ap.get("class") in {"UEFA", "DOMESTIC_CUP", "CUP_OTHER"} else "NO",
            "home_next_is_uefa_or_cup": "YES" if hn.get("class") in {"UEFA", "DOMESTIC_CUP", "CUP_OTHER"} else "NO",
            "away_next_is_uefa_or_cup": "YES" if an.get("class") in {"UEFA", "DOMESTIC_CUP", "CUP_OTHER"} else "NO",
            "injuries_count": len(injuries), "home_injuries_count": len(h_inj), "away_injuries_count": len(a_inj),
            "injuries_json": json.dumps(injuries, ensure_ascii=False, separators=(",", ":")),
            "lineups_available": "YES" if lineups else "NO", "home_formation": hl.get("formation", ""), "away_formation": al.get("formation", ""),
            "home_coach": hl.get("coach", ""), "away_coach": al.get("coach", ""),
            "home_start_xi_json": json.dumps(hl.get("xi", []), ensure_ascii=False, separators=(",", ":")),
            "away_start_xi_json": json.dumps(al.get("xi", []), ensure_ascii=False, separators=(",", ":")),
            "context_only": "YES", "notes": notes,
        }
        snapshots.append(row)
        new_rows.append(row)
        done.add((forward_id, snapshot_type))

    write_csv(SNAPSHOTS, FIELDS, snapshots)
    latest_by_id = {}
    for r in snapshots:
        fid = r.get("forward_id") or ""
        cur = latest_by_id.get(fid)
        if cur is None or (r.get("captured_at_utc") or "") > (cur.get("captured_at_utc") or ""):
            latest_by_id[fid] = r
    write_csv(LATEST, FIELDS, list(latest_by_id.values()))

    meta = {
        "run_at_utc": iso(now), "status": "OK", "active_forward_rows": len(active),
        "new_context_snapshots": len(new_rows), "total_context_snapshots": len(snapshots),
        "fixture_checks": fixture_checks, "schedule_calls": schedule_calls, "injury_calls": injury_calls, "lineup_calls": lineup_calls,
        "warnings": warnings,
        "policy": {
            "role": "context-only; never changes R1/R2/R3 eligibility",
            "baseline": "first capture after canonical forward entry",
            "T24": "first capture between 30h and 6h pre-kickoff",
            "T3": "first capture between 6h and 90m pre-kickoff",
            "T60": "captured <=90m only after official lineups are returned",
            "calendar": "previous/next club fixtures across all competitions; raw competition retained",
        },
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
