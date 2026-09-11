#!/usr/bin/env python3
"""Stage71C: prospective individual team-total market capture.

Research data only. No WATCH, no canonical signal, no promotion decision.
Captures all observed full-time team-total lines for PBK's locked 16 leagues.
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

OPS = Path(os.getenv("OPS_DIR", "ops"))
OPENERS = OPS / "stage71c_team_total_openers.csv"
SNAPS = OPS / "stage71c_team_total_snapshots.csv"
CLOSES = OPS / "stage71c_team_total_closes.csv"
META = OPS / "stage71c_last_run.json"

SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2026"))
USER_BOOK = os.getenv("STAGE71C_USER_BOOKMAKER", "Marathonbet").strip()
OPEN_HORIZON_H = float(os.getenv("STAGE71C_OPEN_HORIZON_H", "336"))
TRACK_HORIZON_H = float(os.getenv("STAGE71C_TRACK_HORIZON_H", "72"))
NEXT_PER_LEAGUE = int(os.getenv("STAGE71C_NEXT_PER_LEAGUE", "10"))
HOME_BET_OVERRIDE = os.getenv("STAGE71C_HOME_TEAM_TOTAL_BET_ID", "").strip()
AWAY_BET_OVERRIDE = os.getenv("STAGE71C_AWAY_TEAM_TOTAL_BET_ID", "").strip()

LEAGUES = {
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
    "Austrian Bundesliga": 218,
    "Belgian Pro League": 144,
    "Danish Superliga": 119,
    "A Lyga": 362,
    "Virsliga": 365,
    "Eredivisie": 88,
    "Eliteserien": 103,
    "Ekstraklasa": 106,
    "Primeira Liga": 94,
    "Super Lig": 203,
    "Scottish Premiership": 179,
}

OPEN_FIELDS = [
    "market_key", "api_fixture_id", "league", "league_id", "captured_at_utc", "kickoff_utc",
    "home_team", "away_team", "team_side", "team_name", "line", "bet_id", "bet_name",
    "open_b365_over", "open_b365_under", "open_p_over", "open_p_under", "status", "source",
]
SNAP_FIELDS = [
    "market_key", "api_fixture_id", "league", "league_id", "captured_at_utc", "kickoff_utc",
    "minutes_to_kickoff", "home_team", "away_team", "team_side", "team_name", "line",
    "bet_id", "bet_name", "b365_over", "b365_under", "p_over", "p_under",
    "open_p_over", "over_move_pp", "user_bookmaker", "user_over", "user_under",
    "api_odds_update_utc",
]
CLOSE_FIELDS = [
    "market_key", "api_fixture_id", "league", "league_id", "locked_at_utc", "kickoff_utc",
    "close_observed_at_utc", "close_gap_minutes", "home_team", "away_team", "team_side",
    "team_name", "line", "bet_id", "bet_name", "open_p_over", "close_p_over",
    "movement_pp", "bet365_close_over", "bet365_close_under", "user_bookmaker",
    "user_close_over", "user_close_under", "status", "note",
]


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if dt else ""


def parse_iso(v):
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def fnum(v):
    try:
        x = float(str(v).strip())
        return x if math.isfinite(x) else None
    except Exception:
        return None


def norm(v):
    return " ".join(str(v or "").strip().lower().replace("-", " ").replace("_", " ").split())


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def novig(over_odd, under_odd):
    o, u = fnum(over_odd), fnum(under_odd)
    if o is None or u is None or o <= 1 or u <= 1:
        return None
    io, iu = 1.0/o, 1.0/u
    return io/(io+iu)


def bet_score(name, side):
    low = norm(name)
    if any(x in low for x in ("first half", "second half", "1st half", "2nd half")):
        return 0
    token = "home" if side == "H" else "away"
    if token not in low:
        return 0
    exact = {
        "H": {"home team total goals", "home team goals over under", "home goals over under", "home team over under"},
        "A": {"away team total goals", "away team goals over under", "away goals over under", "away team over under"},
    }[side]
    if low in exact:
        return 100
    score = 0
    if "team" in low: score += 20
    if "goal" in low: score += 30
    if "total" in low: score += 25
    if "over under" in low: score += 35
    if "exact" in low or "number of" in low: score -= 50
    return score if score >= 55 else 0


def discover_bets():
    data = s53.api_get("/odds/bets")
    rows = (data or {}).get("response", [])
    out = {}
    for side, override in (("H", HOME_BET_OVERRIDE), ("A", AWAY_BET_OVERRIDE)):
        if override:
            out[side] = (int(override), "override")
            continue
        candidates = []
        for r in rows:
            bid = int(r.get("id") or 0); name = str(r.get("name") or "").strip()
            sc = bet_score(name, side)
            if bid and sc:
                candidates.append((sc, -len(name), bid, name))
        if not candidates:
            raise RuntimeError(f"Could not discover {'home' if side=='H' else 'away'} team-total bet from /odds/bets")
        candidates.sort(reverse=True)
        _, _, bid, name = candidates[0]
        out[side] = (bid, name)
    if out["H"][0] == out["A"][0]:
        raise RuntimeError("Home and away team-total discovery resolved to same bet id; refusing ambiguous capture")
    return out


def parse_total_value(v):
    text = f"{v.get('value') or ''} {v.get('handicap') or ''}".lower().replace(",", ".")
    if "over" in text:
        side = "O"
    elif "under" in text:
        side = "U"
    else:
        return None
    nums = re.findall(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)", text)
    if not nums:
        return None
    line = fnum(nums[-1])
    if line is None or line < 0 or line > 10:
        return None
    return side, line


def market_prices(api_response, wanted_ids):
    out = {}
    wanted = set(wanted_ids)
    for item in (api_response or {}).get("response", []):
        update = item.get("update") or ""
        for bm in item.get("bookmakers", []) or []:
            bname = bm.get("name") or ""; bkey = norm(bname)
            if not bkey: continue
            for bet in bm.get("bets", []) or []:
                bid = int(bet.get("id") or 0)
                if bid not in wanted: continue
                key = (bkey, bid)
                bucket = out.setdefault(key, {"display": bname, "update": "", "lines": {}})
                if update > (bucket.get("update") or ""): bucket["update"] = update
                for v in bet.get("values", []) or []:
                    parsed = parse_total_value(v); odd = fnum(v.get("odd"))
                    if not parsed or odd is None or odd <= 1: continue
                    oside, line = parsed
                    lb = bucket["lines"].setdefault(line, {"O": None, "U": None})
                    cur = lb[oside]
                    if cur is None or odd > cur: lb[oside] = odd
    return out


def complete_lines(prices, bookmaker, bet_id):
    x = prices.get((norm(bookmaker), int(bet_id)))
    if not x: return {}, ""
    good = {}
    for line, pair in x["lines"].items():
        if fnum(pair.get("O")) is not None and fnum(pair.get("U")) is not None:
            good[line] = pair
    return good, x.get("update") or ""


def upcoming_all():
    out = []
    for lname, lid in LEAGUES.items():
        data = s53.api_get("/fixtures", {"league": lid, "season": SEASON, "next": NEXT_PER_LEAGUE, "timezone": "UTC"})
        for r in (data or {}).get("response", []):
            fx = r.get("fixture", {}) or {}; teams = r.get("teams", {}) or {}
            ko = parse_iso(fx.get("date"))
            if not ko: continue
            out.append({"id": str(fx.get("id") or ""), "league": lname, "league_id": lid, "kickoff": ko,
                        "status": ((fx.get("status") or {}).get("short") or ""),
                        "home": ((teams.get("home") or {}).get("name") or ""),
                        "away": ((teams.get("away") or {}).get("name") or "")})
    return out


def odds_for_fixture(fid):
    return s53.api_get("/odds", {"fixture": fid})


def mkey(fid, side, line):
    return f"TT|{fid}|{side}|{line:g}"


def main():
    now = now_utc(); OPS.mkdir(parents=True, exist_ok=True)
    bets = discover_bets(); wanted_ids = [bets["H"][0], bets["A"][0]]
    openers = read_csv(OPENERS); snaps = read_csv(SNAPS); closes = read_csv(CLOSES)
    open_by = {r.get("market_key", ""): r for r in openers}
    close_by = {r.get("market_key", ""): r for r in closes}
    upcoming = upcoming_all()
    added_open = added_snap = added_close = odds_calls = 0
    warnings = []

    for fx in upcoming:
        hours = (fx["kickoff"] - now).total_seconds()/3600.0
        if hours <= 0 or hours > OPEN_HORIZON_H: continue
        fid = fx["id"]
        has_open = any(str(r.get("api_fixture_id")) == fid for r in openers)
        if has_open and hours > TRACK_HORIZON_H: continue
        try:
            raw = odds_for_fixture(fid); odds_calls += 1
            prices = market_prices(raw, wanted_ids)
        except Exception as exc:
            warnings.append(f"odds {fid}: {exc}"); continue

        for side in ("H", "A"):
            bid, bname = bets[side]
            b365_lines, upd365 = complete_lines(prices, "Bet365", bid)
            user_lines, upduser = complete_lines(prices, USER_BOOK, bid) if USER_BOOK else ({}, "")
            team_name = fx["home"] if side == "H" else fx["away"]
            for line, pair in sorted(b365_lines.items()):
                key = mkey(fid, side, line); opened = open_by.get(key)
                pnow = novig(pair["O"], pair["U"])
                if pnow is None: continue
                if opened is None:
                    opened = {
                        "market_key": key, "api_fixture_id": fid, "league": fx["league"], "league_id": fx["league_id"],
                        "captured_at_utc": iso(now), "kickoff_utc": iso(fx["kickoff"]), "home_team": fx["home"],
                        "away_team": fx["away"], "team_side": side, "team_name": team_name, "line": f"{line:g}",
                        "bet_id": bid, "bet_name": bname, "open_b365_over": pair["O"], "open_b365_under": pair["U"],
                        "open_p_over": f"{pnow:.8f}", "open_p_under": f"{1-pnow:.8f}", "status": "FROZEN",
                        "source": "API-Football Bet365 first complete team-total pair captured prospectively"
                    }
                    openers.append(opened); open_by[key] = opened; added_open += 1
                if hours <= TRACK_HORIZON_H:
                    popen = fnum(opened.get("open_p_over")); move = pnow-popen if popen is not None else None
                    upair = user_lines.get(line, {})
                    snaps.append({
                        "market_key": key, "api_fixture_id": fid, "league": fx["league"], "league_id": fx["league_id"],
                        "captured_at_utc": iso(now), "kickoff_utc": iso(fx["kickoff"]), "minutes_to_kickoff": f"{hours*60:.1f}",
                        "home_team": fx["home"], "away_team": fx["away"], "team_side": side, "team_name": team_name,
                        "line": f"{line:g}", "bet_id": bid, "bet_name": bname, "b365_over": pair["O"], "b365_under": pair["U"],
                        "p_over": f"{pnow:.8f}", "p_under": f"{1-pnow:.8f}", "open_p_over": opened.get("open_p_over", ""),
                        "over_move_pp": "" if move is None else f"{move:.8f}", "user_bookmaker": USER_BOOK,
                        "user_over": upair.get("O", ""), "user_under": upair.get("U", ""),
                        "api_odds_update_utc": max(upd365, upduser)
                    }); added_snap += 1

    # Freeze observed close from the latest stored pre-kickoff snapshot for each opened market.
    snap_by = {}
    for r in snaps:
        key = r.get("market_key", ""); t = parse_iso(r.get("captured_at_utc")); ko = parse_iso(r.get("kickoff_utc"))
        if not key or not t or not ko or t > ko: continue
        old = snap_by.get(key)
        if old is None or (parse_iso(old.get("captured_at_utc")) or datetime.min.replace(tzinfo=timezone.utc)) < t:
            snap_by[key] = r
    for key, opened in list(open_by.items()):
        if key in close_by: continue
        ko = parse_iso(opened.get("kickoff_utc"))
        if not ko or now < ko: continue
        s = snap_by.get(key)
        if not s: continue
        ct = parse_iso(s.get("captured_at_utc")); popen = fnum(opened.get("open_p_over")); pclose = fnum(s.get("p_over"))
        move = pclose-popen if popen is not None and pclose is not None else None
        row = {
            "market_key": key, "api_fixture_id": opened.get("api_fixture_id", ""), "league": opened.get("league", ""),
            "league_id": opened.get("league_id", ""), "locked_at_utc": iso(now), "kickoff_utc": opened.get("kickoff_utc", ""),
            "close_observed_at_utc": s.get("captured_at_utc", ""),
            "close_gap_minutes": "" if not ct else f"{(ko-ct).total_seconds()/60:.1f}",
            "home_team": opened.get("home_team", ""), "away_team": opened.get("away_team", ""),
            "team_side": opened.get("team_side", ""), "team_name": opened.get("team_name", ""), "line": opened.get("line", ""),
            "bet_id": opened.get("bet_id", ""), "bet_name": opened.get("bet_name", ""), "open_p_over": opened.get("open_p_over", ""),
            "close_p_over": s.get("p_over", ""), "movement_pp": "" if move is None else f"{move:.8f}",
            "bet365_close_over": s.get("b365_over", ""), "bet365_close_under": s.get("b365_under", ""),
            "user_bookmaker": USER_BOOK, "user_close_over": s.get("user_over", ""), "user_close_under": s.get("user_under", ""),
            "status": "OBSERVED_CLOSE_FROZEN", "note": "Latest stored pre-kickoff price for the exact same team-side and line"
        }
        closes.append(row); close_by[key] = row; added_close += 1

    write_csv(OPENERS, OPEN_FIELDS, openers); write_csv(SNAPS, SNAP_FIELDS, snaps); write_csv(CLOSES, CLOSE_FIELDS, closes)
    meta = {
        "run_at_utc": iso(now), "status": "OK", "mode": "PROSPECTIVE_CAPTURE_ONLY", "leagues": len(LEAGUES),
        "fixtures_scanned": len(upcoming), "home_team_total_bet_id": bets["H"][0], "home_team_total_bet_name": bets["H"][1],
        "away_team_total_bet_id": bets["A"][0], "away_team_total_bet_name": bets["A"][1], "odds_calls": odds_calls,
        "new_openers": added_open, "new_snapshots": added_snap, "new_closes": added_close,
        "total_openers": len(openers), "total_snapshots": len(snaps), "total_closes": len(closes),
        "signals_created": 0, "warnings": warnings[:50]
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
