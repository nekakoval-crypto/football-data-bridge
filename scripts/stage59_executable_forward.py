#!/usr/bin/env python3
"""Stage 59: user-executable paper forward ledger.

This layer keeps research/market execution separate from what the user can
actually access. It never changes R1/R2/R3, trigger prices, or the canonical
Stage53 execution snapshot.

Policy:
  * freeze the first observed allowlisted user price after the signal;
  * treat that as standardized PAPER user execution, not proof of a real bet;
  * calculate user_profit_u only from that frozen user price;
  * preserve canonical market profit separately;
  * use user close from Stage54 when available for user-price CLV.
"""
from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
ODDS = OPS / "odds_snapshots.csv"
CLOSING = OPS / "closing_log.csv"
USER_EXEC = OPS / "user_execution_log.csv"
USER_VIEW = OPS / "user_forward_view.csv"
META = OPS / "stage59_last_run.json"

USER_EXEC_FIELDS = [
    "forward_id", "rule", "api_fixture_id", "signal_screened_at_utc",
    "captured_at_utc", "current_kickoff_utc", "minutes_to_kickoff",
    "selection", "stake_u", "bookmaker", "odds", "verified",
    "execution_type", "source",
]

USER_VIEW_FIELDS = [
    "forward_id", "rule", "api_fixture_id", "kickoff_utc", "home_team", "away_team",
    "selection", "stake_u", "status", "result",
    "trigger_selected_odds", "market_execution_odds", "market_execution_bookmaker",
    "paper_user_execution_odds", "paper_user_execution_bookmaker", "paper_user_execution_at_utc",
    "user_close_odds", "user_close_bookmaker", "user_price_ratio_clv_pct",
    "market_profit_u", "user_profit_u", "user_execution_status", "notes",
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


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def fnum(value):
    try:
        x = float(str(value).strip())
        return x if math.isfinite(x) else None
    except Exception:
        return None


def trigger_selected(row):
    sel = row.get("bet_selection")
    if sel == "Away":
        return row.get("trigger_b365_away") or ""
    if sel == "Draw":
        return row.get("trigger_b365_draw") or ""
    if sel == "Home":
        return row.get("trigger_b365_home") or ""
    return ""


def paper_profit(row, user_exec):
    status = row.get("status") or ""
    if status == "VOID":
        return "0.000"
    if status != "SETTLED":
        return ""
    odds = fnum(user_exec.get("odds"))
    stake = fnum(row.get("stake_u")) or 1.0
    if not odds:
        return ""
    result = row.get("result") or ""
    sel = row.get("bet_selection") or ""
    won = (
        (sel == "Away" and result == "A")
        or (sel == "Draw" and result == "D")
        or (sel == "Home" and result == "H")
    )
    return f"{stake * (odds - 1.0) if won else -stake:.3f}"


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    forward = read_csv(FORWARD)
    snapshots = read_csv(ODDS)
    closing = read_csv(CLOSING)
    user_exec_rows = read_csv(USER_EXEC)

    existing = {r.get("forward_id"): r for r in user_exec_rows if r.get("forward_id")}
    forward_by_id = {r.get("forward_id"): r for r in forward if r.get("forward_id")}

    # Freeze only the first allowlisted executable observation after the signal.
    candidates = {}
    for s in snapshots:
        fid = s.get("forward_id") or ""
        if not fid or fid in existing or not s.get("user_best_odds") or not s.get("user_best_book"):
            continue
        if s.get("user_allowlist_configured") != "YES":
            continue
        bet = forward_by_id.get(fid)
        if not bet:
            continue
        captured = parse_iso(s.get("captured_at_utc"))
        screened = parse_iso(bet.get("screened_at_utc"))
        if not captured or (screened and captured < screened):
            continue
        cur = candidates.get(fid)
        if cur is None or captured < cur[0]:
            candidates[fid] = (captured, s, bet)

    new_exec = 0
    for fid, (_, s, bet) in candidates.items():
        row = {
            "forward_id": fid,
            "rule": bet.get("rule") or "",
            "api_fixture_id": bet.get("api_fixture_id") or "",
            "signal_screened_at_utc": bet.get("screened_at_utc") or "",
            "captured_at_utc": s.get("captured_at_utc") or "",
            "current_kickoff_utc": s.get("current_kickoff_utc") or "",
            "minutes_to_kickoff": s.get("minutes_to_kickoff") or "",
            "selection": bet.get("bet_selection") or "",
            "stake_u": bet.get("stake_u") or "",
            "bookmaker": s.get("user_best_book") or "",
            "odds": s.get("user_best_odds") or "",
            "verified": "YES",
            "execution_type": "PAPER_FIRST_OBSERVED_ALLOWLISTED_PRICE",
            "source": "Stage54 odds_snapshots user_best",
        }
        user_exec_rows.append(row)
        existing[fid] = row
        new_exec += 1

    # Append-only by forward_id: keep chronological order for auditability.
    user_exec_rows.sort(key=lambda r: (r.get("captured_at_utc") or "", r.get("forward_id") or ""))
    write_csv(USER_EXEC, USER_EXEC_FIELDS, user_exec_rows)

    close_by_id = {r.get("forward_id"): r for r in closing if r.get("forward_id")}
    view = []
    with_exec = 0
    settled_with_user_profit = 0
    for bet in forward:
        fid = bet.get("forward_id") or ""
        if not fid:
            continue
        ue = existing.get(fid) or {}
        cl = close_by_id.get(fid) or {}
        if ue:
            with_exec += 1
        user_close = fnum(cl.get("user_close_odds"))
        user_open = fnum(ue.get("odds"))
        user_clv = ((user_open / user_close) - 1.0) * 100.0 if user_open and user_close else None
        up = paper_profit(bet, ue)
        if up != "" and bet.get("status") == "SETTLED":
            settled_with_user_profit += 1

        view.append({
            "forward_id": fid,
            "rule": bet.get("rule") or "",
            "api_fixture_id": bet.get("api_fixture_id") or "",
            "kickoff_utc": cl.get("current_kickoff_utc") or (
                f"{bet.get('match_date')}T{bet.get('kickoff_time')}:00Z"
                if bet.get("match_date") and bet.get("kickoff_time") else ""
            ),
            "home_team": bet.get("home_team") or "",
            "away_team": bet.get("away_team") or "",
            "selection": bet.get("bet_selection") or "",
            "stake_u": bet.get("stake_u") or "",
            "status": bet.get("status") or "",
            "result": bet.get("result") or "",
            "trigger_selected_odds": trigger_selected(bet),
            "market_execution_odds": bet.get("execution_odds") or "",
            "market_execution_bookmaker": bet.get("execution_bookmaker") or "",
            "paper_user_execution_odds": ue.get("odds") or "",
            "paper_user_execution_bookmaker": ue.get("bookmaker") or "",
            "paper_user_execution_at_utc": ue.get("captured_at_utc") or "",
            "user_close_odds": cl.get("user_close_odds") or "",
            "user_close_bookmaker": cl.get("user_close_bookmaker") or "",
            "user_price_ratio_clv_pct": "" if user_clv is None else f"{user_clv:.3f}",
            "market_profit_u": bet.get("profit_u") or "",
            "user_profit_u": up,
            "user_execution_status": "FROZEN" if ue else "WAITING_EXECUTABLE_PRICE",
            "notes": "paper user execution; not proof of a real placed bet",
        })

    view.sort(key=lambda r: (r.get("kickoff_utc") or "", r.get("forward_id") or ""))
    write_csv(USER_VIEW, USER_VIEW_FIELDS, view)

    meta = {
        "run_at_utc": now,
        "status": "OK",
        "canonical_forward_rows": len(forward),
        "new_user_execution_rows": new_exec,
        "frozen_user_execution_rows": with_exec,
        "settled_rows_with_user_profit": settled_with_user_profit,
        "policy": {
            "paper_user_execution": "first observed allowlisted price after signal; immutable once frozen",
            "real_bet_claim": "never inferred from API observation",
            "canonical_market_execution": "preserved separately and never overwritten",
            "user_profit": "calculated only from frozen paper user execution",
        },
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
