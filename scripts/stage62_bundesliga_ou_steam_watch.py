#!/usr/bin/env python3
"""Stage 62: Bundesliga Over 2.5 Steam prospective WATCH.

Research-only watcher for the preregistered Stage62 Bundesliga O1 candidate.
It never writes to canonical ops/forward_log.csv and never creates a bet.

Historical O1 definition:
  Bet365 close no-vig P(Over 2.5) - first no-vig P(Over 2.5) >= +0.03;
  historical settlement price = Bet365 closing Over 2.5.

Prospective evidence collected here:
  * freeze first complete Bet365 O/U 2.5 pair per Bundesliga fixture;
  * append timestamped Bet365 + Marathonbet O/U 2.5 snapshots near kickoff;
  * record first +0.03 crossing once (WATCH only, not a bet);
  * after kickoff freeze latest observed pre-kickoff snapshot as observed close;
  * classify whether exact historical O1 remained true at observed close.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53

OUT = Path(os.getenv("OPS_DIR", "ops"))
OPENERS = OUT / "stage62_ou_openers.csv"
SNAPS = OUT / "stage62_ou_snapshots.csv"
CROSSINGS = OUT / "stage62_ou_crossings.csv"
CLOSES = OUT / "stage62_ou_closes.csv"
META = OUT / "stage62_last_run.json"

BUNDESLIGA_ID = int(os.getenv("STAGE62_BUNDESLIGA_LEAGUE_ID", "78"))
SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2026"))
USER_BOOK = os.getenv("STAGE62_USER_BOOKMAKER", "Marathonbet").strip()
OPEN_CAPTURE_HORIZON_H = float(os.getenv("STAGE62_OPEN_CAPTURE_HORIZON_H", "336"))
TRACK_HORIZON_H = float(os.getenv("STAGE62_TRACK_HORIZON_H", "72"))
THRESHOLD = float(os.getenv("STAGE62_OVER_STEAM_THRESHOLD", "0.03"))
BET_ID_OVERRIDE = os.getenv("STAGE62_OU_BET_ID", "").strip()

OPEN_FIELDS = [
    "api_fixture_id", "captured_at_utc", "kickoff_utc", "home_team", "away_team",
    "ou_bet_id", "ou_bet_name", "open_b365_over25", "open_b365_under25",
    "open_p_over25", "open_p_under25", "source", "status",
]
SNAP_FIELDS = [
    "api_fixture_id", "captured_at_utc", "kickoff_utc", "minutes_to_kickoff",
    "fixture_status", "home_team", "away_team", "ou_bet_id", "ou_bet_name",
    "b365_over25", "b365_under25", "p_over25", "p_under25",
    "open_p_over25", "over_move_pp", "o1_current_qualified",
    "user_bookmaker", "user_over25", "user_under25", "api_odds_update_utc",
]
CROSS_FIELDS = [
    "watch_id", "api_fixture_id", "crossed_at_utc", "kickoff_utc",
    "minutes_to_kickoff", "home_team", "away_team", "ou_bet_id", "ou_bet_name",
    "open_p_over25", "cross_p_over25", "movement_pp",
    "bet365_cross_over25", "bet365_cross_under25",
    "user_bookmaker", "user_cross_over25", "user_cross_under25",
    "status", "note",
]
CLOSE_FIELDS = [
    "watch_id", "api_fixture_id", "locked_at_utc", "kickoff_utc",
    "close_observed_at_utc", "close_gap_minutes", "home_team", "away_team",
    "ou_bet_id", "ou_bet_name", "open_p_over25", "close_p_over25", "movement_pp",
    "bet365_close_over25", "bet365_close_under25", "user_bookmaker",
    "user_close_over25", "user_close_under25", "o1_close_qualified",
    "crossing_recorded", "first_crossed_at_utc", "first_cross_gap_minutes",
    "user_over25_at_first_cross", "status", "note",
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


def norm(s):
    return " ".join(str(s or "").strip().lower().split())


def novig_over(over_odd, under_odd):
    o, u = fnum(over_odd), fnum(under_odd)
    if o is None or u is None or o <= 1 or u <= 1:
        return None
    io, iu = 1.0 / o, 1.0 / u
    z = io + iu
    return io / z


def discover_ou_bet():
    if BET_ID_OVERRIDE:
        return int(BET_ID_OVERRIDE), "override"
    data = s53.api_get("/odds/bets")
    candidates = []
    for x in (data or {}).get("response", []):
        name = str(x.get("name") or "").strip()
        low = norm(name).replace(" / ", "/")
        bid = int(x.get("id") or 0)
        if not bid:
            continue
        score = 0
        if low == "goals over/under":
            score = 100
        elif low in {"over/under", "goal over/under", "total goals over/under"}:
            score = 90
        elif "over/under" in low and "goal" in low and "half" not in low and "team" not in low:
            score = 70
        elif "over/under" in low and "half" not in low and "team" not in low:
            score = 40
        if score:
            candidates.append((score, bid, name))
    if not candidates:
        raise RuntimeError("Could not discover a generic goals Over/Under bet id from /odds/bets")
    candidates.sort(reverse=True)
    _, bid, name = candidates[0]
    return bid, name


def value_side_25(v):
    label = norm(v.get("value"))
    handicap = str(v.get("handicap") or "").strip().lower()
    text = f"{label} {handicap}".replace(",", ".")
    has25 = bool(re.search(r"(^|[^0-9])2\.5([^0-9]|$)", text))
    if not has25:
        return ""
    if "over" in text:
        return "O"
    if "under" in text:
        return "U"
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
            x = out.setdefault(key, {"O": None, "U": None, "update": "", "display": bname})
            for bet in bm.get("bets", []) or []:
                if int(bet.get("id") or 0) != int(bet_id):
                    continue
                for v in bet.get("values", []) or []:
                    side = value_side_25(v)
                    odd = fnum(v.get("odd"))
                    if not side or odd is None or odd <= 1:
                        continue
                    cur = x.get(side)
                    if cur is None or odd > cur:
                        x[side] = odd
            if update and update > (x.get("update") or ""):
                x["update"] = update
    return out


def book_pair(bookmap, name):
    x = bookmap.get(norm(name))
    if not x:
        return None
    if fnum(x.get("O")) is None or fnum(x.get("U")) is None:
        return None
    return x


def upcoming_bundesliga():
    data = s53.api_get(
        "/fixtures",
        {"league": BUNDESLIGA_ID, "season": SEASON, "next": 20, "timezone": "UTC"},
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


def fetch_odds(fid, bet_id):
    return s53.api_get("/odds", {"fixture": fid, "bet": bet_id})


def main():
    now = now_utc()
    OUT.mkdir(parents=True, exist_ok=True)

    bet_id, bet_name = discover_ou_bet()
    openers, _ = read_csv(OPENERS)
    snaps, _ = read_csv(SNAPS)
    crossings, _ = read_csv(CROSSINGS)
    closes, _ = read_csv(CLOSES)

    opener_by = {str(r.get("api_fixture_id") or ""): r for r in openers}
    crossing_by = {str(r.get("api_fixture_id") or ""): r for r in crossings}
    close_by = {str(r.get("api_fixture_id") or ""): r for r in closes}

    upcoming = upcoming_bundesliga()
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
            try:
                fx = fixture_state(fid)
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
                b365 = book_pair(bookmap, "Bet365")
                user = book_pair(bookmap, USER_BOOK) if USER_BOOK else None

                if opened is None and b365:
                    p_open = novig_over(b365["O"], b365["U"])
                    if p_open is not None:
                        opened = {
                            "api_fixture_id": fid,
                            "captured_at_utc": iso(now),
                            "kickoff_utc": iso(kickoff),
                            "home_team": fx["home"],
                            "away_team": fx["away"],
                            "ou_bet_id": bet_id,
                            "ou_bet_name": bet_name,
                            "open_b365_over25": b365["O"],
                            "open_b365_under25": b365["U"],
                            "open_p_over25": f"{p_open:.8f}",
                            "open_p_under25": f"{1-p_open:.8f}",
                            "source": "API-Football Bet365 first complete O/U 2.5 snapshot captured by Stage62",
                            "status": "FROZEN",
                        }
                        openers.append(opened)
                        opener_by[fid] = opened
                        added_openers += 1

                if opened is not None and b365:
                    p_now = novig_over(b365["O"], b365["U"])
                    p_open = fnum(opened.get("open_p_over25"))
                    move = (p_now - p_open) if p_now is not None and p_open is not None else None
                    qualified = move is not None and move >= THRESHOLD
                    update = ""
                    for xx in (b365, user):
                        if xx and (xx.get("update") or "") > update:
                            update = xx.get("update") or ""

                    snaps.append({
                        "api_fixture_id": fid,
                        "captured_at_utc": iso(now),
                        "kickoff_utc": iso(kickoff),
                        "minutes_to_kickoff": f"{minutes:.1f}",
                        "fixture_status": status,
                        "home_team": fx["home"],
                        "away_team": fx["away"],
                        "ou_bet_id": bet_id,
                        "ou_bet_name": bet_name,
                        "b365_over25": b365["O"],
                        "b365_under25": b365["U"],
                        "p_over25": "" if p_now is None else f"{p_now:.8f}",
                        "p_under25": "" if p_now is None else f"{1-p_now:.8f}",
                        "open_p_over25": "" if p_open is None else f"{p_open:.8f}",
                        "over_move_pp": "" if move is None else f"{move:.8f}",
                        "o1_current_qualified": "YES" if qualified else "NO",
                        "user_bookmaker": USER_BOOK,
                        "user_over25": user["O"] if user else "",
                        "user_under25": user["U"] if user else "",
                        "api_odds_update_utc": update,
                    })
                    added_snaps += 1

                    if qualified and fid not in crossing_by:
                        watch_id = f"ST62-O1-{fid}"
                        cr = {
                            "watch_id": watch_id,
                            "api_fixture_id": fid,
                            "crossed_at_utc": iso(now),
                            "kickoff_utc": iso(kickoff),
                            "minutes_to_kickoff": f"{minutes:.1f}",
                            "home_team": fx["home"],
                            "away_team": fx["away"],
                            "ou_bet_id": bet_id,
                            "ou_bet_name": bet_name,
                            "open_p_over25": f"{p_open:.8f}" if p_open is not None else "",
                            "cross_p_over25": f"{p_now:.8f}" if p_now is not None else "",
                            "movement_pp": f"{move:.8f}" if move is not None else "",
                            "bet365_cross_over25": b365["O"],
                            "bet365_cross_under25": b365["U"],
                            "user_bookmaker": USER_BOOK,
                            "user_cross_over25": user["O"] if user else "",
                            "user_cross_under25": user["U"] if user else "",
                            "status": "WATCH",
                            "note": "Research-only first +3pp Over no-vig crossing; not a canonical bet",
                        }
                        crossings.append(cr)
                        crossing_by[fid] = cr
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
                captured, s = max(candidates, key=lambda z: z[0])
                p_open = fnum(opened.get("open_p_over25"))
                p_close = fnum(s.get("p_over25"))
                move = (p_close - p_open) if p_open is not None and p_close is not None else None
                qualified = move is not None and move >= THRESHOLD
                cr = crossing_by.get(fid, {})
                close = {
                    "watch_id": f"ST62-O1-{fid}",
                    "api_fixture_id": fid,
                    "locked_at_utc": iso(now),
                    "kickoff_utc": iso(kickoff),
                    "close_observed_at_utc": s.get("captured_at_utc") or "",
                    "close_gap_minutes": f"{(kickoff-captured).total_seconds()/60:.1f}",
                    "home_team": fx["home"],
                    "away_team": fx["away"],
                    "ou_bet_id": bet_id,
                    "ou_bet_name": bet_name,
                    "open_p_over25": "" if p_open is None else f"{p_open:.8f}",
                    "close_p_over25": "" if p_close is None else f"{p_close:.8f}",
                    "movement_pp": "" if move is None else f"{move:.8f}",
                    "bet365_close_over25": s.get("b365_over25") or "",
                    "bet365_close_under25": s.get("b365_under25") or "",
                    "user_bookmaker": USER_BOOK,
                    "user_close_over25": s.get("user_over25") or "",
                    "user_close_under25": s.get("user_under25") or "",
                    "o1_close_qualified": "YES" if qualified else "NO",
                    "crossing_recorded": "YES" if cr else "NO",
                    "first_crossed_at_utc": cr.get("crossed_at_utc") or "",
                    "first_cross_gap_minutes": cr.get("minutes_to_kickoff") or "",
                    "user_over25_at_first_cross": cr.get("user_cross_over25") or "",
                    "status": "CLOSE_QUALIFIED_WATCH" if qualified else "CLOSED_NOT_QUALIFIED",
                    "note": "Observed close only; historical Stage62 O1 classification; not a canonical bet",
                }
                closes.append(close)
                close_by[fid] = close
                added_closes += 1

    write_csv(OPENERS, OPEN_FIELDS, openers)
    write_csv(SNAPS, SNAP_FIELDS, snaps)
    write_csv(CROSSINGS, CROSS_FIELDS, crossings)
    write_csv(CLOSES, CLOSE_FIELDS, closes)

    close_qualified = sum(1 for r in closes if r.get("o1_close_qualified") == "YES")
    meta = {
        "run_at_utc": iso(now),
        "status": "OK",
        "scope": "Bundesliga O/U 2.5 Over Steam only",
        "season": SEASON,
        "ou_bet_id": bet_id,
        "ou_bet_name": bet_name,
        "over_steam_threshold_no_vig_pp": THRESHOLD,
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
        "close_qualified_total": close_qualified,
        "policy": {
            "canonical_forward": "UNCHANGED",
            "crossing": "WATCH only; not a bet",
            "historical_match": "requires observed closing Over no-vig probability >= opener + 0.03",
            "execution_evidence": "Marathonbet Over 2.5 price captured at first crossing and observed close when available",
        },
        "warnings": warnings,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
