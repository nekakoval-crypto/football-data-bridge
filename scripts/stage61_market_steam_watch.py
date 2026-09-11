#!/usr/bin/env python3
"""Stage 61: Premier League Favorite-Steam forward watch.

Research-only watcher for the preregistered Stage61 M1 candidate.

This script never creates or settles canonical forward bets. It collects the
prospective evidence needed to determine whether the historical close-defined
pattern is actually executable:

* first complete Bet365 1X2 snapshot is frozen per Premier League fixture;
* timestamped current Bet365 + Marathonbet snapshots are appended near kickoff;
* first +0.03 no-vig favorite-steam crossing is recorded once;
* after kickoff, the latest observed pre-kickoff snapshot is frozen as the
  observed close and the exact historical M1 condition is evaluated.

Historical M1:
  opening unique team favorite remains the unique closing favorite and
  its normalized no-vig probability rises by >= 0.03; bet favorite at close.

Crossing != historical qualification. A fixture can cross +0.03 and later
reverse. That is precisely why this is a WATCH rather than canonical R4.
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
OPENERS = OUT / "stage61_market_openers.csv"
SNAPS = OUT / "stage61_market_snapshots.csv"
CROSSINGS = OUT / "stage61_market_crossings.csv"
CLOSES = OUT / "stage61_market_closes.csv"
META = OUT / "stage61_last_run.json"

PL_LEAGUE_ID = int(os.getenv("STAGE61_PL_LEAGUE_ID", "39"))
SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2026"))
MATCH_WINNER_BET_ID = int(os.getenv("API_FOOTBALL_MATCH_WINNER_BET_ID", "1"))
USER_BOOK = os.getenv("STAGE61_USER_BOOKMAKER", "Marathonbet").strip()
OPEN_CAPTURE_HORIZON_H = float(os.getenv("STAGE61_OPEN_CAPTURE_HORIZON_H", "336"))
TRACK_HORIZON_H = float(os.getenv("STAGE61_TRACK_HORIZON_H", "72"))
THRESHOLD = float(os.getenv("STAGE61_STEAM_THRESHOLD", "0.03"))

OPEN_FIELDS = [
    "api_fixture_id", "captured_at_utc", "kickoff_utc", "home_team", "away_team",
    "open_b365_home", "open_b365_draw", "open_b365_away",
    "open_p_home", "open_p_draw", "open_p_away", "open_favorite",
    "source", "status",
]
SNAP_FIELDS = [
    "api_fixture_id", "captured_at_utc", "kickoff_utc", "minutes_to_kickoff",
    "fixture_status", "home_team", "away_team",
    "b365_home", "b365_draw", "b365_away",
    "p_home", "p_draw", "p_away", "current_favorite",
    "open_favorite", "open_favorite_p", "current_open_favorite_p",
    "open_favorite_move_pp", "m1_current_qualified",
    "user_bookmaker", "user_home", "user_draw", "user_away",
    "user_open_favorite_odds", "api_odds_update_utc",
]
CROSS_FIELDS = [
    "watch_id", "api_fixture_id", "crossed_at_utc", "kickoff_utc",
    "minutes_to_kickoff", "home_team", "away_team", "opening_favorite",
    "open_favorite_p", "cross_favorite_p", "movement_pp",
    "bet365_cross_odds", "user_bookmaker", "user_cross_odds",
    "status", "note",
]
CLOSE_FIELDS = [
    "watch_id", "api_fixture_id", "locked_at_utc", "kickoff_utc",
    "close_observed_at_utc", "close_gap_minutes", "home_team", "away_team",
    "opening_favorite", "closing_favorite",
    "open_favorite_p", "close_open_favorite_p", "movement_pp",
    "bet365_close_home", "bet365_close_draw", "bet365_close_away",
    "bet365_close_favorite_odds", "user_bookmaker",
    "user_close_favorite_odds", "m1_close_qualified",
    "crossing_recorded", "first_crossed_at_utc", "first_cross_gap_minutes",
    "user_odds_at_first_cross", "status", "note",
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


def norm_book(s):
    return " ".join(str(s or "").strip().lower().split())


def novig(h, d, a):
    vals = [fnum(h), fnum(d), fnum(a)]
    if any(v is None or v <= 1 for v in vals):
        return None
    inv = [1.0 / v for v in vals]
    z = sum(inv)
    return {"H": inv[0] / z, "D": inv[1] / z, "A": inv[2] / z}


def team_favorite(h, d, a):
    vals = {"H": fnum(h), "D": fnum(d), "A": fnum(a)}
    if any(v is None for v in vals.values()):
        return ""
    m = min(vals.values())
    winners = [k for k, v in vals.items() if abs(v - m) < 1e-12]
    if len(winners) != 1 or winners[0] == "D":
        return ""
    return winners[0]


def prices_by_book(api_response, home, away):
    out = {}
    for sel, odd, book, update in s53.unpack_matchwinner(api_response, home, away):
        key = norm_book(book)
        if not key:
            continue
        x = out.setdefault(key, {"H": None, "D": None, "A": None, "update": "", "display": book})
        side = {"home": "H", "draw": "D", "away": "A"}.get(sel)
        if not side:
            continue
        cur = x.get(side)
        if cur is None or odd > cur:
            x[side] = odd
        if update and update > (x.get("update") or ""):
            x["update"] = update
    return out


def upcoming_pl():
    data = s53.api_get(
        "/fixtures",
        {"league": PL_LEAGUE_ID, "season": SEASON, "next": 20, "timezone": "UTC"},
    )
    out = []
    for x in (data or {}).get("response", []):
        fx = x.get("fixture", {}) or {}
        teams = x.get("teams", {}) or {}
        dt = parse_iso(fx.get("date"))
        if not dt:
            continue
        out.append({
            "id": str(fx.get("id") or ""),
            "kickoff": dt,
            "status": ((fx.get("status") or {}).get("short") or ""),
            "home": ((teams.get("home") or {}).get("name") or ""),
            "away": ((teams.get("away") or {}).get("name") or ""),
        })
    return out


def fixture_state(fid):
    data = s53.api_get("/fixtures", {"id": fid, "timezone": "UTC"})
    if not (data or {}).get("response"):
        return None
    x = data["response"][0]
    fx = x.get("fixture", {}) or {}
    teams = x.get("teams", {}) or {}
    return {
        "id": str(fx.get("id") or fid),
        "kickoff": parse_iso(fx.get("date")),
        "status": ((fx.get("status") or {}).get("short") or ""),
        "home": ((teams.get("home") or {}).get("name") or ""),
        "away": ((teams.get("away") or {}).get("name") or ""),
    }


def fetch_odds(fx):
    return s53.api_get("/odds", {"fixture": fx["id"], "bet": MATCH_WINNER_BET_ID})


def book_triplet(bookmap, name):
    x = bookmap.get(norm_book(name))
    if not x:
        return None
    if not all(fnum(x.get(k)) for k in ("H", "D", "A")):
        return None
    return x


def odds_for_side(trip, side):
    if not trip or side not in ("H", "D", "A"):
        return None
    return fnum(trip.get(side))


def opener_from_snapshot(fx, now, bet365):
    p = novig(bet365["H"], bet365["D"], bet365["A"])
    fav = team_favorite(bet365["H"], bet365["D"], bet365["A"])
    if not p or not fav:
        return None
    return {
        "api_fixture_id": fx["id"],
        "captured_at_utc": iso(now),
        "kickoff_utc": iso(fx["kickoff"]),
        "home_team": fx["home"],
        "away_team": fx["away"],
        "open_b365_home": bet365["H"],
        "open_b365_draw": bet365["D"],
        "open_b365_away": bet365["A"],
        "open_p_home": f"{p['H']:.8f}",
        "open_p_draw": f"{p['D']:.8f}",
        "open_p_away": f"{p['A']:.8f}",
        "open_favorite": fav,
        "source": "API-Football Bet365 first complete snapshot captured by Stage61",
        "status": "FROZEN",
    }


def main():
    now = now_utc()
    OUT.mkdir(parents=True, exist_ok=True)

    openers, _ = read_csv(OPENERS)
    snaps, _ = read_csv(SNAPS)
    crossings, _ = read_csv(CROSSINGS)
    closes, _ = read_csv(CLOSES)

    opener_by = {str(r.get("api_fixture_id") or ""): r for r in openers}
    crossing_by = {str(r.get("api_fixture_id") or ""): r for r in crossings}
    close_by = {str(r.get("api_fixture_id") or ""): r for r in closes}

    upcoming = upcoming_pl()
    up_by = {x["id"]: x for x in upcoming if x["id"]}

    active_ids = set(up_by)
    for fid in opener_by:
        if fid and fid not in close_by:
            active_ids.add(fid)

    added_openers = 0
    added_snaps = 0
    added_crossings = 0
    added_closes = 0
    odds_calls = 0
    fixture_state_calls = 0
    warnings = []

    for fid in sorted(active_ids):
        fx = up_by.get(fid)
        if fx is None:
            try:
                fx = fixture_state(fid)
                fixture_state_calls += 1
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
        finalized = fid in close_by

        need_odds = False
        if now < kickoff and status in {"NS", "TBD", "PST"}:
            if opened is None and 0 < hours <= OPEN_CAPTURE_HORIZON_H:
                need_odds = True
            elif opened is not None and 0 < hours <= TRACK_HORIZON_H:
                need_odds = True

        if need_odds:
            try:
                od = fetch_odds(fx)
                odds_calls += 1
            except Exception as exc:
                warnings.append(f"odds {fid}: {exc}")
                od = None

            if od:
                bookmap = prices_by_book(od, fx["home"], fx["away"])
                bet365 = book_triplet(bookmap, "Bet365")
                user = book_triplet(bookmap, USER_BOOK) if USER_BOOK else None

                if opened is None and bet365:
                    op = opener_from_snapshot(fx, now, bet365)
                    if op:
                        openers.append(op)
                        opener_by[fid] = op
                        opened = op
                        added_openers += 1

                if opened is not None and bet365:
                    p = novig(bet365["H"], bet365["D"], bet365["A"])
                    cur_fav = team_favorite(bet365["H"], bet365["D"], bet365["A"])
                    open_fav = opened.get("open_favorite") or ""
                    op_col = {"H": "open_p_home", "A": "open_p_away"}.get(open_fav, "")
                    op_p = fnum(opened.get(op_col)) if op_col else None
                    cur_open_p = p.get(open_fav) if p and open_fav in ("H", "A") else None
                    move = (cur_open_p - op_p) if cur_open_p is not None and op_p is not None else None
                    qualified = bool(
                        open_fav in ("H", "A")
                        and cur_fav == open_fav
                        and move is not None
                        and move >= THRESHOLD
                    )
                    update = ""
                    for x in (bet365, user):
                        if x and (x.get("update") or "") > update:
                            update = x.get("update") or ""

                    snap = {
                        "api_fixture_id": fid,
                        "captured_at_utc": iso(now),
                        "kickoff_utc": iso(kickoff),
                        "minutes_to_kickoff": f"{minutes:.1f}",
                        "fixture_status": status,
                        "home_team": fx["home"],
                        "away_team": fx["away"],
                        "b365_home": bet365["H"],
                        "b365_draw": bet365["D"],
                        "b365_away": bet365["A"],
                        "p_home": f"{p['H']:.8f}" if p else "",
                        "p_draw": f"{p['D']:.8f}" if p else "",
                        "p_away": f"{p['A']:.8f}" if p else "",
                        "current_favorite": cur_fav,
                        "open_favorite": open_fav,
                        "open_favorite_p": "" if op_p is None else f"{op_p:.8f}",
                        "current_open_favorite_p": "" if cur_open_p is None else f"{cur_open_p:.8f}",
                        "open_favorite_move_pp": "" if move is None else f"{move:.8f}",
                        "m1_current_qualified": "YES" if qualified else "NO",
                        "user_bookmaker": USER_BOOK,
                        "user_home": user["H"] if user else "",
                        "user_draw": user["D"] if user else "",
                        "user_away": user["A"] if user else "",
                        "user_open_favorite_odds": odds_for_side(user, open_fav) or "",
                        "api_odds_update_utc": update,
                    }
                    snaps.append(snap)
                    added_snaps += 1

                    if qualified and fid not in crossing_by:
                        cross = {
                            "watch_id": f"M1PL|{fid}",
                            "api_fixture_id": fid,
                            "crossed_at_utc": iso(now),
                            "kickoff_utc": iso(kickoff),
                            "minutes_to_kickoff": f"{minutes:.1f}",
                            "home_team": fx["home"],
                            "away_team": fx["away"],
                            "opening_favorite": open_fav,
                            "open_favorite_p": f"{op_p:.8f}",
                            "cross_favorite_p": f"{cur_open_p:.8f}",
                            "movement_pp": f"{move:.8f}",
                            "bet365_cross_odds": odds_for_side(bet365, open_fav) or "",
                            "user_bookmaker": USER_BOOK,
                            "user_cross_odds": odds_for_side(user, open_fav) or "",
                            "status": "WATCH_CROSSED",
                            "note": "First observed +0.03 no-vig favorite-steam crossing; not a canonical bet",
                        }
                        crossings.append(cross)
                        crossing_by[fid] = cross
                        added_crossings += 1

        started = status not in {"NS", "TBD", "PST"} or now >= kickoff
        if opened is not None and started and not finalized:
            candidates = []
            for s in snaps:
                if str(s.get("api_fixture_id") or "") != fid:
                    continue
                captured = parse_iso(s.get("captured_at_utc"))
                if captured and captured <= kickoff:
                    candidates.append((captured, s))
            if candidates:
                captured, s = max(candidates, key=lambda z: z[0])
                open_fav = opened.get("open_favorite") or ""
                close_fav = s.get("current_favorite") or ""
                op_col = {"H": "open_p_home", "A": "open_p_away"}.get(open_fav, "")
                op_p = fnum(opened.get(op_col)) if op_col else None
                cp = fnum(s.get("current_open_favorite_p"))
                move = cp - op_p if cp is not None and op_p is not None else None
                qualified = bool(
                    open_fav in ("H", "A")
                    and close_fav == open_fav
                    and move is not None
                    and move >= THRESHOLD
                )
                cross = crossing_by.get(fid)
                side_col = {"H": "b365_home", "A": "b365_away"}.get(open_fav, "")
                close_fav_odds = s.get(side_col) if side_col else ""
                c = {
                    "watch_id": f"M1PL|{fid}",
                    "api_fixture_id": fid,
                    "locked_at_utc": iso(now),
                    "kickoff_utc": iso(kickoff),
                    "close_observed_at_utc": s.get("captured_at_utc") or "",
                    "close_gap_minutes": f"{(kickoff-captured).total_seconds()/60:.1f}",
                    "home_team": fx["home"],
                    "away_team": fx["away"],
                    "opening_favorite": open_fav,
                    "closing_favorite": close_fav,
                    "open_favorite_p": "" if op_p is None else f"{op_p:.8f}",
                    "close_open_favorite_p": "" if cp is None else f"{cp:.8f}",
                    "movement_pp": "" if move is None else f"{move:.8f}",
                    "bet365_close_home": s.get("b365_home") or "",
                    "bet365_close_draw": s.get("b365_draw") or "",
                    "bet365_close_away": s.get("b365_away") or "",
                    "bet365_close_favorite_odds": close_fav_odds or "",
                    "user_bookmaker": USER_BOOK,
                    "user_close_favorite_odds": s.get("user_open_favorite_odds") or "",
                    "m1_close_qualified": "YES" if qualified else "NO",
                    "crossing_recorded": "YES" if cross else "NO",
                    "first_crossed_at_utc": (cross or {}).get("crossed_at_utc") or "",
                    "first_cross_gap_minutes": (cross or {}).get("minutes_to_kickoff") or "",
                    "user_odds_at_first_cross": (cross or {}).get("user_cross_odds") or "",
                    "status": "CLOSE_QUALIFIED_WATCH" if qualified else "CLOSED_NOT_QUALIFIED",
                    "note": "Observed pre-kickoff close; Stage61 research-only, no canonical R4",
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
        "scope": "Premier League only",
        "season": SEASON,
        "steam_threshold_no_vig_pp": THRESHOLD,
        "open_capture_horizon_hours": OPEN_CAPTURE_HORIZON_H,
        "track_horizon_hours": TRACK_HORIZON_H,
        "user_bookmaker": USER_BOOK,
        "upcoming_fixtures_seen": len(upcoming),
        "active_fixture_ids": len(active_ids),
        "odds_api_calls": odds_calls,
        "fixture_state_api_calls": fixture_state_calls,
        "new_openers": added_openers,
        "new_snapshots": added_snaps,
        "new_crossings": added_crossings,
        "new_closes": added_closes,
        "total_openers": len(openers),
        "total_snapshots": len(snaps),
        "total_crossings": len(crossings),
        "total_closes": len(closes),
        "close_qualified_total": sum(1 for r in closes if r.get("m1_close_qualified") == "YES"),
        "policy": {
            "canonical_forward": "UNCHANGED",
            "crossing": "WATCH only; not a bet",
            "historical_match": "requires same opening/closing favorite and >=+0.03 no-vig movement at observed close",
            "execution_evidence": "Marathonbet price captured at first crossing and observed close when available",
        },
        "warnings": warnings,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
