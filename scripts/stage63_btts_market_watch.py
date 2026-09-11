#!/usr/bin/env python3
"""Stage 63: Big-5 BTTS (ОЗ) prospective market-movement WATCH.

No historical BTTS first/close odds exist in the canonical 10-year dataset, so
this stage is prospective data collection only. It never writes canonical
forward bets and never claims a historical edge.

Protocol:
* freeze first complete Bet365 BTTS Yes/No pair per upcoming Big-5 fixture;
* append timestamped Bet365 + Marathonbet snapshots near kickoff;
* record first +/-3pp no-vig movement from opener as research WATCH events;
* after kickoff freeze latest observed pre-kickoff snapshot as observed close.
"""
from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53

OUT = Path(os.getenv("OPS_DIR", "ops"))
OPENERS = OUT / "stage63_btts_openers.csv"
SNAPS = OUT / "stage63_btts_snapshots.csv"
CROSSINGS = OUT / "stage63_btts_crossings.csv"
CLOSES = OUT / "stage63_btts_closes.csv"
META = OUT / "stage63_last_run.json"

SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2026"))
USER_BOOK = os.getenv("STAGE63_USER_BOOKMAKER", "Marathonbet").strip()
OPEN_CAPTURE_HORIZON_H = float(os.getenv("STAGE63_OPEN_CAPTURE_HORIZON_H", "336"))
TRACK_HORIZON_H = float(os.getenv("STAGE63_TRACK_HORIZON_H", "72"))
THRESHOLD = float(os.getenv("STAGE63_MOVE_THRESHOLD", "0.03"))
BET_ID_OVERRIDE = os.getenv("STAGE63_BTTS_BET_ID", "").strip()

LEAGUES = {
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
}

OPEN_FIELDS = [
    "api_fixture_id", "league", "league_id", "captured_at_utc", "kickoff_utc",
    "home_team", "away_team", "btts_bet_id", "btts_bet_name",
    "open_b365_yes", "open_b365_no", "open_p_yes", "open_p_no", "source", "status",
]
SNAP_FIELDS = [
    "api_fixture_id", "league", "league_id", "captured_at_utc", "kickoff_utc",
    "minutes_to_kickoff", "fixture_status", "home_team", "away_team",
    "btts_bet_id", "btts_bet_name", "b365_yes", "b365_no", "p_yes", "p_no",
    "open_p_yes", "yes_move_pp", "yes_steam_watch", "no_steam_watch",
    "user_bookmaker", "user_yes", "user_no", "api_odds_update_utc",
]
CROSS_FIELDS = [
    "watch_id", "api_fixture_id", "league", "league_id", "direction",
    "display_selection", "crossed_at_utc", "kickoff_utc", "minutes_to_kickoff",
    "home_team", "away_team", "open_p_yes", "cross_p_yes", "movement_yes_pp",
    "bet365_cross_yes", "bet365_cross_no", "user_bookmaker", "user_cross_yes",
    "user_cross_no", "user_cross_selected_odds", "status", "note",
]
CLOSE_FIELDS = [
    "api_fixture_id", "league", "league_id", "locked_at_utc", "kickoff_utc",
    "close_observed_at_utc", "close_gap_minutes", "home_team", "away_team",
    "open_p_yes", "close_p_yes", "movement_yes_pp", "yes_close_watch", "no_close_watch",
    "bet365_close_yes", "bet365_close_no", "user_bookmaker", "user_close_yes",
    "user_close_no", "yes_crossing_recorded", "no_crossing_recorded", "status", "note",
]


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def fnum(x):
    try:
        v = float(str(x).strip())
        return v if math.isfinite(v) else None
    except Exception:
        return None


def norm(s):
    return " ".join(str(s or "").strip().lower().replace("-", " ").split())


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


def novig_yes(yes_odd, no_odd):
    y, n = fnum(yes_odd), fnum(no_odd)
    if y is None or n is None or y <= 1 or n <= 1:
        return None
    iy, ino = 1.0 / y, 1.0 / n
    return iy / (iy + ino)


def discover_btts_bet():
    if BET_ID_OVERRIDE:
        return int(BET_ID_OVERRIDE), "override"
    data = s53.api_get("/odds/bets")
    candidates = []
    for x in (data or {}).get("response", []):
        bid = int(x.get("id") or 0)
        name = str(x.get("name") or "").strip()
        low = norm(name)
        if not bid:
            continue
        score = 0
        if low in {"both teams score", "both teams to score"}:
            score = 100
        elif "both teams" in low and "score" in low and "half" not in low:
            score = 90
        elif "btts" in low:
            score = 80
        if score:
            candidates.append((score, -len(name), bid, name))
    if not candidates:
        raise RuntimeError("Could not discover generic BTTS / Both Teams To Score bet id")
    candidates.sort(reverse=True)
    _, _, bid, name = candidates[0]
    return bid, name


def value_side(v):
    label = norm(v.get("value"))
    if label in {"yes", "y", "both teams to score yes", "both teams score yes"}:
        return "Y"
    if label in {"no", "n", "both teams to score no", "both teams score no"}:
        return "N"
    if "yes" in label and "no" not in label:
        return "Y"
    if "no" in label and "yes" not in label:
        return "N"
    return ""


def prices_by_book(api_response, bet_id):
    out = {}
    for item in (api_response or {}).get("response", []):
        update = item.get("update") or ""
        for bm in item.get("bookmakers", []) or []:
            bname = bm.get("name") or ""
            key = norm(bname)
            if not key:
                continue
            x = out.setdefault(key, {"Y": None, "N": None, "update": "", "display": bname})
            for bet in bm.get("bets", []) or []:
                if int(bet.get("id") or 0) != int(bet_id):
                    continue
                for v in bet.get("values", []) or []:
                    side = value_side(v)
                    odd = fnum(v.get("odd"))
                    if not side or odd is None or odd <= 1:
                        continue
                    cur = x.get(side)
                    if cur is None or odd > cur:
                        x[side] = odd
            if update and update > (x.get("update") or ""):
                x["update"] = update
    return out


def pair(bookmap, name):
    x = bookmap.get(norm(name))
    if not x or fnum(x.get("Y")) is None or fnum(x.get("N")) is None:
        return None
    return x


def upcoming_all():
    out = []
    for league_name, league_id in LEAGUES.items():
        data = s53.api_get(
            "/fixtures",
            {"league": league_id, "season": SEASON, "next": 20, "timezone": "UTC"},
        )
        for x in (data or {}).get("response", []):
            fx = x.get("fixture", {}) or {}
            teams = x.get("teams", {}) or {}
            dt = parse_iso(fx.get("date"))
            if not dt:
                continue
            out.append({
                "id": str(fx.get("id") or ""),
                "league": league_name,
                "league_id": league_id,
                "kickoff": dt,
                "status": ((fx.get("status") or {}).get("short") or ""),
                "home": ((teams.get("home") or {}).get("name") or ""),
                "away": ((teams.get("away") or {}).get("name") or ""),
            })
    return out


def fixture_state(fid, fallback_league="", fallback_league_id=""):
    data = s53.api_get("/fixtures", {"id": fid, "timezone": "UTC"})
    if not (data or {}).get("response"):
        return None
    x = data["response"][0]
    fx = x.get("fixture", {}) or {}
    teams = x.get("teams", {}) or {}
    lg = x.get("league", {}) or {}
    return {
        "id": str(fx.get("id") or fid),
        "league": str(lg.get("name") or fallback_league),
        "league_id": int(lg.get("id") or fallback_league_id or 0),
        "kickoff": parse_iso(fx.get("date")),
        "status": ((fx.get("status") or {}).get("short") or ""),
        "home": ((teams.get("home") or {}).get("name") or ""),
        "away": ((teams.get("away") or {}).get("name") or ""),
    }


def fetch_odds(fid, bet_id):
    return s53.api_get("/odds", {"fixture": fid, "bet": bet_id})


def main():
    now = now_utc()
    OUT.mkdir(parents=True, exist_ok=True)

    bet_id, bet_name = discover_btts_bet()
    openers, _ = read_csv(OPENERS)
    snaps, _ = read_csv(SNAPS)
    crossings, _ = read_csv(CROSSINGS)
    closes, _ = read_csv(CLOSES)

    opener_by = {str(r.get("api_fixture_id") or ""): r for r in openers}
    close_by = {str(r.get("api_fixture_id") or ""): r for r in closes}
    cross_ids = {r.get("watch_id") for r in crossings if r.get("watch_id")}

    upcoming = upcoming_all()
    up_by = {x["id"]: x for x in upcoming if x["id"]}
    active_ids = set(up_by)
    for fid in opener_by:
        if fid and fid not in close_by:
            active_ids.add(fid)

    added_openers = added_snaps = added_crossings = added_closes = 0
    odds_calls = fixture_calls = 0
    warnings = []

    for fid in sorted(active_ids):
        fx = up_by.get(fid)
        if fx is None:
            op = opener_by.get(fid, {})
            try:
                fx = fixture_state(fid, op.get("league") or "", op.get("league_id") or "")
                fixture_calls += 1
            except Exception as exc:
                warnings.append(f"fixture {fid}: {exc}")
                continue
        if not fx or not fx.get("kickoff"):
            continue

        kickoff = fx["kickoff"]
        status = fx.get("status") or ""
        minutes = (kickoff - now).total_seconds() / 60.0
        hours = minutes / 60.0
        opened = opener_by.get(fid)

        need_odds = False
        if now < kickoff and status in {"NS", "TBD", "PST"}:
            if opened is None and 0 < hours <= OPEN_CAPTURE_HORIZON_H:
                need_odds = True
            elif opened is not None and 0 < hours <= TRACK_HORIZON_H:
                need_odds = True

        if need_odds:
            try:
                od = fetch_odds(fid, bet_id)
                odds_calls += 1
            except Exception as exc:
                warnings.append(f"odds {fid}: {exc}")
                od = None

            if od:
                bookmap = prices_by_book(od, bet_id)
                b365 = pair(bookmap, "Bet365")
                user = pair(bookmap, USER_BOOK) if USER_BOOK else None

                if opened is None and b365:
                    p_open = novig_yes(b365["Y"], b365["N"])
                    if p_open is not None:
                        opened = {
                            "api_fixture_id": fid,
                            "league": fx.get("league") or "",
                            "league_id": fx.get("league_id") or "",
                            "captured_at_utc": iso(now),
                            "kickoff_utc": iso(kickoff),
                            "home_team": fx["home"],
                            "away_team": fx["away"],
                            "btts_bet_id": bet_id,
                            "btts_bet_name": bet_name,
                            "open_b365_yes": b365["Y"],
                            "open_b365_no": b365["N"],
                            "open_p_yes": f"{p_open:.8f}",
                            "open_p_no": f"{1-p_open:.8f}",
                            "source": "API-Football Bet365 first complete BTTS snapshot captured by Stage63",
                            "status": "FROZEN",
                        }
                        openers.append(opened)
                        opener_by[fid] = opened
                        added_openers += 1

                if opened is not None and b365:
                    p_now = novig_yes(b365["Y"], b365["N"])
                    p_open = fnum(opened.get("open_p_yes"))
                    move = (p_now - p_open) if p_now is not None and p_open is not None else None
                    yes_q = move is not None and move >= THRESHOLD
                    no_q = move is not None and move <= -THRESHOLD
                    update = ""
                    for xx in (b365, user):
                        if xx and (xx.get("update") or "") > update:
                            update = xx.get("update") or ""

                    snaps.append({
                        "api_fixture_id": fid,
                        "league": opened.get("league") or fx.get("league") or "",
                        "league_id": opened.get("league_id") or fx.get("league_id") or "",
                        "captured_at_utc": iso(now),
                        "kickoff_utc": iso(kickoff),
                        "minutes_to_kickoff": f"{minutes:.1f}",
                        "fixture_status": status,
                        "home_team": fx["home"],
                        "away_team": fx["away"],
                        "btts_bet_id": bet_id,
                        "btts_bet_name": bet_name,
                        "b365_yes": b365["Y"],
                        "b365_no": b365["N"],
                        "p_yes": "" if p_now is None else f"{p_now:.8f}",
                        "p_no": "" if p_now is None else f"{1-p_now:.8f}",
                        "open_p_yes": "" if p_open is None else f"{p_open:.8f}",
                        "yes_move_pp": "" if move is None else f"{move:.8f}",
                        "yes_steam_watch": "YES" if yes_q else "NO",
                        "no_steam_watch": "YES" if no_q else "NO",
                        "user_bookmaker": USER_BOOK,
                        "user_yes": user["Y"] if user else "",
                        "user_no": user["N"] if user else "",
                        "api_odds_update_utc": update,
                    })
                    added_snaps += 1

                    for direction, qualified in (("YES", yes_q), ("NO", no_q)):
                        wid = f"BTTS_{direction}|{fid}"
                        if not qualified or wid in cross_ids:
                            continue
                        crossings.append({
                            "watch_id": wid,
                            "api_fixture_id": fid,
                            "league": opened.get("league") or fx.get("league") or "",
                            "league_id": opened.get("league_id") or fx.get("league_id") or "",
                            "direction": direction,
                            "display_selection": "ОЗ — Да" if direction == "YES" else "ОЗ — Нет",
                            "crossed_at_utc": iso(now),
                            "kickoff_utc": iso(kickoff),
                            "minutes_to_kickoff": f"{minutes:.1f}",
                            "home_team": fx["home"],
                            "away_team": fx["away"],
                            "open_p_yes": "" if p_open is None else f"{p_open:.8f}",
                            "cross_p_yes": "" if p_now is None else f"{p_now:.8f}",
                            "movement_yes_pp": "" if move is None else f"{move:.8f}",
                            "bet365_cross_yes": b365["Y"],
                            "bet365_cross_no": b365["N"],
                            "user_bookmaker": USER_BOOK,
                            "user_cross_yes": user["Y"] if user else "",
                            "user_cross_no": user["N"] if user else "",
                            "user_cross_selected_odds": (user["Y"] if direction == "YES" else user["N"]) if user else "",
                            "status": "WATCH_ONLY",
                            "note": "Prospective research crossing; not a canonical bet signal",
                        })
                        cross_ids.add(wid)
                        added_crossings += 1

        started = status not in {"NS", "TBD", "PST"} or now >= kickoff
        if started and opened is not None and fid not in close_by:
            candidates = []
            for s in snaps:
                if str(s.get("api_fixture_id") or "") != fid:
                    continue
                captured = parse_iso(s.get("captured_at_utc"))
                if captured and captured <= kickoff:
                    candidates.append((captured, s))
            if candidates:
                captured, s = max(candidates, key=lambda x: x[0])
                move = fnum(s.get("yes_move_pp"))
                c = {
                    "api_fixture_id": fid,
                    "league": opened.get("league") or fx.get("league") or "",
                    "league_id": opened.get("league_id") or fx.get("league_id") or "",
                    "locked_at_utc": iso(now),
                    "kickoff_utc": iso(kickoff),
                    "close_observed_at_utc": s.get("captured_at_utc") or "",
                    "close_gap_minutes": f"{(kickoff-captured).total_seconds()/60:.1f}",
                    "home_team": fx["home"],
                    "away_team": fx["away"],
                    "open_p_yes": opened.get("open_p_yes") or "",
                    "close_p_yes": s.get("p_yes") or "",
                    "movement_yes_pp": s.get("yes_move_pp") or "",
                    "yes_close_watch": "YES" if move is not None and move >= THRESHOLD else "NO",
                    "no_close_watch": "YES" if move is not None and move <= -THRESHOLD else "NO",
                    "bet365_close_yes": s.get("b365_yes") or "",
                    "bet365_close_no": s.get("b365_no") or "",
                    "user_bookmaker": USER_BOOK,
                    "user_close_yes": s.get("user_yes") or "",
                    "user_close_no": s.get("user_no") or "",
                    "yes_crossing_recorded": "YES" if f"BTTS_YES|{fid}" in cross_ids else "NO",
                    "no_crossing_recorded": "YES" if f"BTTS_NO|{fid}" in cross_ids else "NO",
                    "status": "OBSERVED_CLOSE",
                    "note": "Latest Stage63 pre-kickoff snapshot; research only",
                }
                closes.append(c)
                close_by[fid] = c
                added_closes += 1

    write_csv(OPENERS, OPEN_FIELDS, openers)
    write_csv(SNAPS, SNAP_FIELDS, snaps)
    write_csv(CROSSINGS, CROSS_FIELDS, crossings)
    write_csv(CLOSES, CLOSE_FIELDS, closes)

    meta = {
        "run_at_utc": iso(now),
        "status": "OK",
        "scope": "Big-5 BTTS prospective market watch",
        "season": SEASON,
        "btts_bet_id": bet_id,
        "btts_bet_name": bet_name,
        "movement_threshold_no_vig_pp": THRESHOLD,
        "open_capture_horizon_hours": OPEN_CAPTURE_HORIZON_H,
        "track_horizon_hours": TRACK_HORIZON_H,
        "user_bookmaker": USER_BOOK,
        "upcoming_fixtures_seen": len(upcoming),
        "active_fixture_ids": len(active_ids),
        "odds_api_calls": odds_calls,
        "fixture_state_api_calls": fixture_calls,
        "new_openers": added_openers,
        "new_snapshots": added_snaps,
        "new_crossings": added_crossings,
        "new_closes": added_closes,
        "total_openers": len(openers),
        "total_snapshots": len(snaps),
        "total_crossings": len(crossings),
        "total_closes": len(closes),
        "policy": {
            "canonical_forward": "UNCHANGED",
            "historical_edge": "NONE CLAIMED — historical BTTS first/close odds unavailable in canonical dataset",
            "crossing": "WATCH only; not a bet",
            "display_market": "ОЗ — Да / ОЗ — Нет",
            "execution_evidence": "Marathonbet Yes/No captured at crossing and observed close when available",
        },
        "warnings": warnings,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
