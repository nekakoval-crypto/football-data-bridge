#!/usr/bin/env python3
"""Stage 54: forward governance, fixture-state tracking and observed closing odds.

This layer does NOT change R1/R2/R3 or any frozen trigger/execution price.
It adds operational evidence around existing forward rows:
  * fixture status/date by API-Football fixture_id (robust to postponements)
  * append-only pre-match odds snapshots for the selected outcome
  * observed closing = latest captured pre-kickoff snapshot
  * optional user-bookmaker allowlist (PBK_BOOKMAKER_ALLOWLIST)
  * API-Football based settlement / void / review state

The original Stage 53 forward row remains the source of trigger and execution data.
"""
from __future__ import annotations

import csv
import json
import math
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://v3.football.api-sports.io"
OUT_DIR = Path(os.getenv("OPS_DIR", "ops"))
FORWARD_LOG = OUT_DIR / "forward_log.csv"
SNAPSHOTS = OUT_DIR / "odds_snapshots.csv"
CLOSING_LOG = OUT_DIR / "closing_log.csv"
EVENT_LOG = OUT_DIR / "fixture_events.csv"
RUN_META = OUT_DIR / "stage54_last_run.json"

BET365_ID = int(os.getenv("API_FOOTBALL_BET365_ID", "8"))
MATCH_WINNER_BET_ID = int(os.getenv("API_FOOTBALL_MATCH_WINNER_BET_ID", "1"))

SNAPSHOT_FIELDS = [
    "forward_id", "rule", "api_fixture_id", "captured_at_utc", "fixture_status",
    "current_kickoff_utc", "minutes_to_kickoff", "selection", "best_odds", "best_book",
    "bet365_odds", "user_best_odds", "user_best_book", "user_allowlist_configured",
    "api_odds_update_utc",
]
CLOSING_FIELDS = [
    "forward_id", "rule", "api_fixture_id", "locked_at_utc", "current_kickoff_utc",
    "selection", "closing_observed_at_utc", "closing_gap_minutes", "closing_odds",
    "closing_bookmaker", "bet365_close_odds", "user_close_odds", "user_close_bookmaker",
    "execution_odds", "price_ratio_clv_pct", "closing_reason",
]
EVENT_FIELDS = [
    "event_id", "api_fixture_id", "observed_at_utc", "event_type", "old_value", "new_value", "details"
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
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def row_original_kickoff(row):
    try:
        return datetime.fromisoformat(f"{row['match_date']}T{row['kickoff_time']}:00+00:00")
    except Exception:
        return None


def api_get(path, params=None):
    key = os.getenv("API_FOOTBALL_KEY", "").strip()
    if not key:
        raise RuntimeError("API_FOOTBALL_KEY is missing")
    qs = urllib.parse.urlencode(params or {})
    url = API_BASE + path + ("?" + qs if qs else "")
    req = urllib.request.Request(url, headers={"x-apisports-key": key, "User-Agent": "football-data-bridge/4.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("errors"):
        raise RuntimeError(f"API-Football {path}: {data['errors']}")
    return data


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


def append_note(row, text):
    old = (row.get("notes") or "").strip()
    if text in old:
        return
    row["notes"] = (old + ("; " if old else "") + text).strip()


def norm_book(s):
    return " ".join(str(s or "").strip().lower().split())


def allowlist():
    raw = os.getenv("PBK_BOOKMAKER_ALLOWLIST", "")
    return {norm_book(x) for x in raw.split(",") if norm_book(x)}


def matchwinner_prices(api_response, selection):
    wanted = {"Away": "away", "Draw": "draw", "Home": "home"}.get(selection, selection.lower())
    prices = []
    for item in api_response.get("response", []):
        update = item.get("update") or ""
        for bm in item.get("bookmakers", []) or []:
            bname = bm.get("name") or ""
            bid = bm.get("id")
            for bet in bm.get("bets", []) or []:
                if int(bet.get("id") or 0) != MATCH_WINNER_BET_ID:
                    continue
                for v in bet.get("values", []) or []:
                    label = str(v.get("value") or "").strip().lower()
                    odd = fnum(v.get("odd"))
                    if not odd:
                        continue
                    if label in {"home", "1"}:
                        sel = "home"
                    elif label in {"draw", "x"}:
                        sel = "draw"
                    elif label in {"away", "2"}:
                        sel = "away"
                    else:
                        continue
                    if sel == wanted:
                        prices.append({"odd": odd, "book": bname, "book_id": bid, "update": update})
    return prices


def fixture_state(fixture_id):
    d = api_get("/fixtures", {"id": fixture_id, "timezone": "UTC"})
    if not d.get("response"):
        return None
    x = d["response"][0]
    fx = x.get("fixture", {})
    return {
        "date": parse_iso(fx.get("date")),
        "status": (fx.get("status", {}) or {}).get("short") or "",
        "status_long": (fx.get("status", {}) or {}).get("long") or "",
        "home_winner": (x.get("teams", {}).get("home", {}) or {}).get("winner"),
        "away_winner": (x.get("teams", {}).get("away", {}) or {}).get("winner"),
        "home_goals": (x.get("goals", {}) or {}).get("home"),
        "away_goals": (x.get("goals", {}) or {}).get("away"),
    }


def outcome_from_fixture(st):
    hg = st.get("home_goals")
    ag = st.get("away_goals")
    if hg is None or ag is None:
        return ""
    try:
        hg, ag = int(hg), int(ag)
    except Exception:
        return ""
    return "H" if hg > ag else "A" if ag > hg else "D"


def profit_for(row, outcome):
    odds = fnum(row.get("execution_odds"))
    stake = fnum(row.get("stake_u")) or 1.0
    if not odds:
        return ""
    sel = row.get("bet_selection")
    won = (sel == "Away" and outcome == "A") or (sel == "Draw" and outcome == "D") or (sel == "Home" and outcome == "H")
    return f"{stake * (odds - 1) if won else -stake:.3f}"


def main():
    now = now_utc()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    forward, forward_fields = read_csv(FORWARD_LOG)
    snapshots, _ = read_csv(SNAPSHOTS)
    closing, _ = read_csv(CLOSING_LOG)
    events, _ = read_csv(EVENT_LOG)
    if not forward:
        write_csv(SNAPSHOTS, SNAPSHOT_FIELDS, snapshots)
        write_csv(CLOSING_LOG, CLOSING_FIELDS, closing)
        write_csv(EVENT_LOG, EVENT_FIELDS, events)
        RUN_META.write_text(json.dumps({"run_at_utc": iso(now), "status": "OK", "open_rows": 0}, indent=2), encoding="utf-8")
        print(json.dumps({"open_rows": 0, "new_snapshots": 0, "new_closes": 0, "new_events": 0}))
        return

    configured = allowlist()
    closing_by_id = {r.get("forward_id"): r for r in closing}
    existing_event_ids = {r.get("event_id") for r in events}
    state_cache = {}
    odds_cache = {}
    added_snapshots = 0
    added_closes = 0
    added_events = 0
    settled = 0
    voided = 0
    review = 0

    open_statuses = {"PAPER", "OPEN", "REVIEW"}
    active = [r for r in forward if r.get("status") in open_statuses]

    for row in active:
        fid = str(row.get("api_fixture_id") or "").strip()
        if not fid:
            continue
        if fid not in state_cache:
            try:
                state_cache[fid] = fixture_state(fid)
            except Exception as e:
                print(f"WARN fixture {fid}: {e}")
                state_cache[fid] = None
        st = state_cache[fid]
        if not st:
            continue
        kickoff = st.get("date")
        status = st.get("status") or ""
        original = row_original_kickoff(row)

        if kickoff and original and abs((kickoff - original).total_seconds()) >= 60:
            eid = f"{fid}|SCHEDULE_CHANGE|{iso(kickoff)}"
            if eid not in existing_event_ids:
                events.append({
                    "event_id": eid, "api_fixture_id": fid, "observed_at_utc": iso(now), "event_type": "SCHEDULE_CHANGE",
                    "old_value": iso(original), "new_value": iso(kickoff), "details": f"API status={status}"
                })
                existing_event_ids.add(eid)
                added_events += 1

        if status in {"PST", "CANC", "ABD", "AWD", "WO"}:
            eid = f"{fid}|STATUS|{status}"
            if eid not in existing_event_ids:
                events.append({
                    "event_id": eid, "api_fixture_id": fid, "observed_at_utc": iso(now), "event_type": "STATUS_CHANGE",
                    "old_value": "", "new_value": status, "details": st.get("status_long") or ""
                })
                existing_event_ids.add(eid)
                added_events += 1

        if status == "CANC" and row.get("status") in {"PAPER", "OPEN", "REVIEW"}:
            row["status"] = "VOID"
            row["result"] = "VOID"
            row["settled_at_utc"] = iso(now)
            row["profit_u"] = "0.000"
            append_note(row, "Stage54: fixture cancelled by API-Football; paper forward voided")
            voided += 1
        elif status in {"ABD", "AWD", "WO"} and row.get("status") in {"PAPER", "OPEN"}:
            row["status"] = "REVIEW"
            append_note(row, f"Stage54: fixture status {status}; manual settlement review required")
            review += 1
        elif status in {"FT", "AET", "PEN"} and row.get("status") in {"PAPER", "OPEN", "REVIEW"}:
            outcome = outcome_from_fixture(st)
            if outcome:
                row["status"] = "SETTLED"
                row["result"] = outcome
                row["settled_at_utc"] = iso(now)
                row["profit_u"] = profit_for(row, outcome)
                append_note(row, f"Stage54: settled by API-Football fixture_id status {status}")
                settled += 1

        # Capture pre-kickoff odds only while the fixture has not started.
        if kickoff and now < kickoff and status in {"NS", "TBD", "PST"} and row.get("status") in {"PAPER", "OPEN", "REVIEW"}:
            if fid not in odds_cache:
                try:
                    odds_cache[fid] = api_get("/odds", {"fixture": fid, "bet": MATCH_WINNER_BET_ID})
                except Exception as e:
                    print(f"WARN odds {fid}: {e}")
                    odds_cache[fid] = None
            od = odds_cache[fid]
            if od:
                prices = matchwinner_prices(od, row.get("bet_selection") or "")
                if prices:
                    best = max(prices, key=lambda x: x["odd"])
                    b365 = [p for p in prices if int(p.get("book_id") or 0) == BET365_ID or norm_book(p.get("book")) == "bet365"]
                    b365_best = max(b365, key=lambda x: x["odd"]) if b365 else None
                    user_prices = [p for p in prices if norm_book(p.get("book")) in configured] if configured else []
                    user_best = max(user_prices, key=lambda x: x["odd"]) if user_prices else None
                    updates = [p.get("update") or "" for p in prices]
                    snapshots.append({
                        "forward_id": row.get("forward_id"), "rule": row.get("rule"), "api_fixture_id": fid,
                        "captured_at_utc": iso(now), "fixture_status": status, "current_kickoff_utc": iso(kickoff),
                        "minutes_to_kickoff": f"{(kickoff-now).total_seconds()/60:.1f}", "selection": row.get("bet_selection"),
                        "best_odds": best["odd"], "best_book": best["book"],
                        "bet365_odds": b365_best["odd"] if b365_best else "",
                        "user_best_odds": user_best["odd"] if user_best else "", "user_best_book": user_best["book"] if user_best else "",
                        "user_allowlist_configured": "YES" if configured else "NO",
                        "api_odds_update_utc": max(updates) if updates else "",
                    })
                    added_snapshots += 1

        # Once kickoff has arrived (or the API reports the match started/finished), freeze the latest captured pre-kickoff snapshot.
        started = status not in {"NS", "TBD", "PST"} or (kickoff and now >= kickoff)
        if started and row.get("forward_id") not in closing_by_id and kickoff:
            candidates = []
            for s in snapshots:
                if s.get("forward_id") != row.get("forward_id"):
                    continue
                captured = parse_iso(s.get("captured_at_utc"))
                if captured and captured <= kickoff:
                    candidates.append((captured, s))
            if candidates:
                captured, s = max(candidates, key=lambda x: x[0])
                exec_odds = fnum(row.get("execution_odds"))
                close_odds = fnum(s.get("best_odds"))
                clv = ((exec_odds / close_odds) - 1) * 100 if exec_odds and close_odds else None
                c = {
                    "forward_id": row.get("forward_id"), "rule": row.get("rule"), "api_fixture_id": fid,
                    "locked_at_utc": iso(now), "current_kickoff_utc": iso(kickoff), "selection": row.get("bet_selection"),
                    "closing_observed_at_utc": s.get("captured_at_utc"),
                    "closing_gap_minutes": f"{(kickoff-captured).total_seconds()/60:.1f}",
                    "closing_odds": s.get("best_odds"), "closing_bookmaker": s.get("best_book"),
                    "bet365_close_odds": s.get("bet365_odds"), "user_close_odds": s.get("user_best_odds"),
                    "user_close_bookmaker": s.get("user_best_book"), "execution_odds": row.get("execution_odds"),
                    "price_ratio_clv_pct": "" if clv is None else f"{clv:.3f}",
                    "closing_reason": "latest observed pre-kickoff snapshot",
                }
                closing.append(c)
                closing_by_id[row.get("forward_id")] = c
                added_closes += 1

    # Preserve the original Stage 53 schema and values; only settlement/status fields and notes can change here.
    write_csv(FORWARD_LOG, forward_fields, forward)
    write_csv(SNAPSHOTS, SNAPSHOT_FIELDS, snapshots)
    write_csv(CLOSING_LOG, CLOSING_FIELDS, closing)
    write_csv(EVENT_LOG, EVENT_FIELDS, events)

    meta = {
        "run_at_utc": iso(now), "status": "OK", "active_forward_rows": len(active),
        "new_snapshots": added_snapshots, "new_closing_rows": added_closes, "new_fixture_events": added_events,
        "settled_rows": settled, "voided_rows": voided, "review_rows": review,
        "user_bookmaker_allowlist_configured": bool(configured),
        "user_bookmaker_allowlist": sorted(configured),
        "policy": {
            "trigger": "Stage53 immutable Bet365 first capture; never rewritten",
            "execution": "Stage53 observed best-market snapshot at signal creation; not assumed to be a user-placed bet",
            "closing": "latest Stage54 observed pre-kickoff best-market Match Winner price",
            "postponement": "follow API fixture_id and log date changes; do not recreate signal",
            "cancelled": "VOID 0u for paper forward",
            "abandoned_awarded_walkover": "REVIEW; no automatic profit",
        },
    }
    RUN_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
