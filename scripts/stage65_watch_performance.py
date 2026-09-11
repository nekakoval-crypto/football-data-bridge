#!/usr/bin/env python3
"""Stage 65: prospective performance for research WATCH events.

Consumes only prospectively recorded first-crossing events from Stages 61-63.
Never mutates canonical forward bets and never substitutes another market after
seeing the result.
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53

OPS = Path(os.getenv("OPS_DIR", "ops"))
LEDGER = OPS / "stage65_watch_ledger.csv"
OUT_JSON = OPS / "watch_performance.json"
OUT_MD = OPS / "watch_performance.md"
META = OPS / "stage65_last_run.json"

S61_CROSS = OPS / "stage61_market_crossings.csv"
S61_CLOSE = OPS / "stage61_market_closes.csv"
S62_CROSS = OPS / "stage62_ou_crossings.csv"
S62_CLOSE = OPS / "stage62_ou_closes.csv"
S63_CROSS = OPS / "stage63_btts_crossings.csv"
S63_CLOSE = OPS / "stage63_btts_closes.csv"

FIELDS = [
    "watch_id", "source_stage", "watch_family", "api_fixture_id", "league",
    "kickoff_utc", "home_team", "away_team", "selection_code", "selection_display",
    "crossed_at_utc", "minutes_to_kickoff", "movement_pp", "stake_u",
    "user_bookmaker", "user_cross_odds", "bet365_cross_odds", "execution_status",
    "close_observed", "close_observed_at_utc", "close_qualified", "close_status",
    "close_movement_pp", "user_close_odds", "bet365_close_odds",
    "fixture_status", "final_home_goals", "final_away_goals", "settlement_status",
    "result", "user_profit_u", "bet365_profit_u", "settled_at_utc", "notes",
]


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fnum(v):
    try:
        x = float(str(v).strip())
        return x if math.isfinite(x) else None
    except Exception:
        return None


def inum(v):
    try:
        return int(v)
    except Exception:
        return None


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def blank_ledger_row():
    return {k: "" for k in FIELDS}


def source_events():
    out = []

    for r in read_csv(S61_CROSS):
        side = r.get("opening_favorite") or ""
        out.append({
            "watch_id": r.get("watch_id") or f"M1PL|{r.get('api_fixture_id') or ''}",
            "source_stage": "Stage61",
            "watch_family": "АПЛ favorite steam",
            "api_fixture_id": r.get("api_fixture_id") or "",
            "league": "Premier League",
            "kickoff_utc": r.get("kickoff_utc") or "",
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "selection_code": side,
            "selection_display": "П1" if side == "H" else ("П2" if side == "A" else side),
            "crossed_at_utc": r.get("crossed_at_utc") or "",
            "minutes_to_kickoff": r.get("minutes_to_kickoff") or "",
            "movement_pp": r.get("movement_pp") or "",
            "stake_u": "1.000",
            "user_bookmaker": r.get("user_bookmaker") or "Marathonbet",
            "user_cross_odds": r.get("user_cross_odds") or "",
            "bet365_cross_odds": r.get("bet365_cross_odds") or "",
        })

    for r in read_csv(S62_CROSS):
        out.append({
            "watch_id": r.get("watch_id") or f"ST62-O1-{r.get('api_fixture_id') or ''}",
            "source_stage": "Stage62",
            "watch_family": "Бундеслига ТБ(2.5) steam",
            "api_fixture_id": r.get("api_fixture_id") or "",
            "league": "Bundesliga",
            "kickoff_utc": r.get("kickoff_utc") or "",
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "selection_code": "O25",
            "selection_display": "ТБ(2.5)",
            "crossed_at_utc": r.get("crossed_at_utc") or "",
            "minutes_to_kickoff": r.get("minutes_to_kickoff") or "",
            "movement_pp": r.get("movement_pp") or "",
            "stake_u": "1.000",
            "user_bookmaker": r.get("user_bookmaker") or "Marathonbet",
            "user_cross_odds": r.get("user_cross_over25") or "",
            "bet365_cross_odds": r.get("bet365_cross_over25") or "",
        })

    for r in read_csv(S63_CROSS):
        direction = r.get("direction") or ""
        out.append({
            "watch_id": r.get("watch_id") or f"BTTS_{direction}|{r.get('api_fixture_id') or ''}",
            "source_stage": "Stage63",
            "watch_family": "Big-5 ОЗ market movement",
            "api_fixture_id": r.get("api_fixture_id") or "",
            "league": r.get("league") or "",
            "kickoff_utc": r.get("kickoff_utc") or "",
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "selection_code": "BTTS_YES" if direction == "YES" else "BTTS_NO",
            "selection_display": r.get("display_selection") or ("ОЗ — Да" if direction == "YES" else "ОЗ — Нет"),
            "crossed_at_utc": r.get("crossed_at_utc") or "",
            "minutes_to_kickoff": r.get("minutes_to_kickoff") or "",
            "movement_pp": r.get("movement_yes_pp") or "",
            "stake_u": "1.000",
            "user_bookmaker": r.get("user_bookmaker") or "Marathonbet",
            "user_cross_odds": r.get("user_cross_selected_odds") or "",
            "bet365_cross_odds": r.get("bet365_cross_yes") if direction == "YES" else r.get("bet365_cross_no"),
        })
    return [x for x in out if x.get("watch_id") and x.get("api_fixture_id")]


def close_maps():
    maps = {"Stage61": {}, "Stage62": {}, "Stage63": {}}
    for r in read_csv(S61_CLOSE):
        wid = r.get("watch_id") or f"M1PL|{r.get('api_fixture_id') or ''}"
        maps["Stage61"][wid] = {
            "close_observed": "YES",
            "close_observed_at_utc": r.get("close_observed_at_utc") or "",
            "close_qualified": r.get("m1_close_qualified") or "NO",
            "close_status": "QUALIFIED_AT_CLOSE" if r.get("m1_close_qualified") == "YES" else "REVERTED_AT_CLOSE",
            "close_movement_pp": r.get("movement_pp") or "",
            "user_close_odds": r.get("user_close_favorite_odds") or "",
            "bet365_close_odds": r.get("bet365_close_favorite_odds") or "",
        }
    for r in read_csv(S62_CLOSE):
        wid = r.get("watch_id") or f"ST62-O1-{r.get('api_fixture_id') or ''}"
        maps["Stage62"][wid] = {
            "close_observed": "YES",
            "close_observed_at_utc": r.get("close_observed_at_utc") or "",
            "close_qualified": r.get("o1_close_qualified") or "NO",
            "close_status": "QUALIFIED_AT_CLOSE" if r.get("o1_close_qualified") == "YES" else "REVERTED_AT_CLOSE",
            "close_movement_pp": r.get("movement_pp") or "",
            "user_close_odds": r.get("user_close_over25") or "",
            "bet365_close_odds": r.get("bet365_close_over25") or "",
        }
    s63_cross = read_csv(S63_CROSS)
    directions_by_fixture = defaultdict(set)
    for r in s63_cross:
        directions_by_fixture[r.get("api_fixture_id") or ""].add(r.get("direction") or "")
    for r in read_csv(S63_CLOSE):
        fid = r.get("api_fixture_id") or ""
        for direction in directions_by_fixture.get(fid, set()):
            wid = f"BTTS_{direction}|{fid}"
            q = r.get("yes_close_watch") == "YES" if direction == "YES" else r.get("no_close_watch") == "YES"
            maps["Stage63"][wid] = {
                "close_observed": "YES",
                "close_observed_at_utc": r.get("close_observed_at_utc") or "",
                "close_qualified": "YES" if q else "NO",
                "close_status": "QUALIFIED_AT_CLOSE" if q else "REVERTED_AT_CLOSE",
                "close_movement_pp": r.get("movement_yes_pp") or "",
                "user_close_odds": r.get("user_close_yes") if direction == "YES" else r.get("user_close_no"),
                "bet365_close_odds": r.get("bet365_close_yes") if direction == "YES" else r.get("bet365_close_no"),
            }
    return maps


def fixture_result(fid):
    data = s53.api_get("/fixtures", {"id": fid, "timezone": "UTC"})
    resp = (data or {}).get("response", [])
    if not resp:
        return None
    x = resp[0]
    fx = x.get("fixture", {}) or {}
    status = ((fx.get("status") or {}).get("short") or "").upper()
    score = x.get("score", {}) or {}
    ft = score.get("fulltime", {}) or {}
    goals = x.get("goals", {}) or {}
    hg = ft.get("home")
    ag = ft.get("away")
    if hg is None:
        hg = goals.get("home")
    if ag is None:
        ag = goals.get("away")
    return {"status": status, "home": inum(hg), "away": inum(ag)}


def settle(selection, hg, ag):
    if hg is None or ag is None:
        return ""
    if selection == "H":
        return "W" if hg > ag else "L"
    if selection == "A":
        return "W" if ag > hg else "L"
    if selection == "O25":
        return "W" if hg + ag >= 3 else "L"
    if selection == "BTTS_YES":
        return "W" if hg > 0 and ag > 0 else "L"
    if selection == "BTTS_NO":
        return "W" if not (hg > 0 and ag > 0) else "L"
    return ""


def profit(result, odds):
    o = fnum(odds)
    if result == "W" and o is not None:
        return o - 1.0
    if result == "L" and o is not None:
        return -1.0
    if result == "VOID" and o is not None:
        return 0.0
    return None


def append_note(row, text):
    old = (row.get("notes") or "").strip()
    if text and text not in old:
        row["notes"] = old + ("; " if old else "") + text


def metric(rows):
    total = len(rows)
    settled = [r for r in rows if r.get("settlement_status") == "SETTLED"]
    pending = [r for r in rows if r.get("settlement_status") == "PENDING"]
    review = [r for r in rows if r.get("settlement_status") == "REVIEW"]
    void = [r for r in rows if r.get("settlement_status") == "VOID"]
    executable = [r for r in rows if fnum(r.get("user_cross_odds")) is not None]
    exec_settled = [r for r in settled if fnum(r.get("user_profit_u")) is not None]
    wins = sum(1 for r in exec_settled if r.get("result") == "W")
    losses = sum(1 for r in exec_settled if r.get("result") == "L")
    stake = float(len(exec_settled))
    pnl = sum(fnum(r.get("user_profit_u")) or 0.0 for r in exec_settled)

    close_obs = [r for r in rows if r.get("close_observed") == "YES"]
    q = [r for r in close_obs if r.get("close_qualified") == "YES"]
    rev = [r for r in close_obs if r.get("close_qualified") == "NO"]

    q_settled = [r for r in q if r.get("settlement_status") == "SETTLED" and fnum(r.get("user_profit_u")) is not None]
    rev_settled = [r for r in rev if r.get("settlement_status") == "SETTLED" and fnum(r.get("user_profit_u")) is not None]
    q_pnl = sum(fnum(r.get("user_profit_u")) or 0.0 for r in q_settled)
    rev_pnl = sum(fnum(r.get("user_profit_u")) or 0.0 for r in rev_settled)

    equity = peak = maxdd = 0.0
    ordered = sorted(exec_settled, key=lambda r: (r.get("kickoff_utc") or "", r.get("watch_id") or ""))
    for r in ordered:
        equity += fnum(r.get("user_profit_u")) or 0.0
        peak = max(peak, equity)
        maxdd = max(maxdd, peak - equity)

    return {
        "crossings": total,
        "pending": len(pending),
        "settled": len(settled),
        "void": len(void),
        "review": len(review),
        "user_price_rows": len(executable),
        "user_execution_coverage_pct": round(100.0 * len(executable) / total, 3) if total else None,
        "user_settled_rows": len(exec_settled),
        "wins": wins,
        "losses": losses,
        "user_profit_u": round(pnl, 3),
        "user_roi_pct": round(100.0 * pnl / stake, 3) if stake else None,
        "close_observed": len(close_obs),
        "close_qualified": len(q),
        "reverted_at_close": len(rev),
        "close_persistence_pct": round(100.0 * len(q) / len(close_obs), 3) if close_obs else None,
        "close_qualified_settled": len(q_settled),
        "close_qualified_profit_u": round(q_pnl, 3),
        "close_qualified_roi_pct": round(100.0 * q_pnl / len(q_settled), 3) if q_settled else None,
        "reverted_settled": len(rev_settled),
        "reverted_profit_u": round(rev_pnl, 3),
        "reverted_roi_pct": round(100.0 * rev_pnl / len(rev_settled), 3) if rev_settled else None,
        "observed_max_drawdown_u": round(maxdd, 3) if exec_settled else None,
    }


def fmt(v, suffix=""):
    return "N/A" if v is None else f"{v}{suffix}"


def main():
    now = now_utc()
    OPS.mkdir(parents=True, exist_ok=True)
    rows = read_csv(LEDGER)
    by_id = {r.get("watch_id"): r for r in rows if r.get("watch_id")}

    new_rows = 0
    for ev in source_events():
        wid = ev["watch_id"]
        if wid in by_id:
            continue
        row = blank_ledger_row()
        row.update(ev)
        row["execution_status"] = "EXECUTABLE_PRICE_CAPTURED" if fnum(ev.get("user_cross_odds")) is not None else "NO_USER_PRICE_AT_CROSSING"
        row["close_observed"] = "NO"
        row["close_qualified"] = ""
        row["close_status"] = "WAITING_CLOSE"
        row["settlement_status"] = "PENDING"
        row["notes"] = "Prospective WATCH only; crossing fields frozen on first ingestion"
        rows.append(row)
        by_id[wid] = row
        new_rows += 1

    cmaps = close_maps()
    for r in rows:
        c = cmaps.get(r.get("source_stage") or "", {}).get(r.get("watch_id") or "")
        if c:
            for k, v in c.items():
                r[k] = "" if v is None else v

    fixture_cache = {}
    fixture_calls = 0
    warnings = []
    unsettled_ids = sorted({
        r.get("api_fixture_id") for r in rows
        if r.get("settlement_status") == "PENDING" and r.get("api_fixture_id")
    })
    for fid in unsettled_ids:
        try:
            fixture_cache[fid] = fixture_result(fid)
            fixture_calls += 1
        except Exception as exc:
            warnings.append(f"fixture {fid}: {exc}")

    newly_settled = 0
    for r in rows:
        if r.get("settlement_status") != "PENDING":
            continue
        fr = fixture_cache.get(r.get("api_fixture_id") or "")
        if not fr:
            continue
        st = fr.get("status") or ""
        r["fixture_status"] = st
        if fr.get("home") is not None:
            r["final_home_goals"] = str(fr["home"])
        if fr.get("away") is not None:
            r["final_away_goals"] = str(fr["away"])

        if st == "FT" and fr.get("home") is not None and fr.get("away") is not None:
            res = settle(r.get("selection_code") or "", fr["home"], fr["away"])
            if res:
                r["settlement_status"] = "SETTLED"
                r["result"] = res
                up = profit(res, r.get("user_cross_odds"))
                bp = profit(res, r.get("bet365_cross_odds"))
                r["user_profit_u"] = "" if up is None else f"{up:.3f}"
                r["bet365_profit_u"] = "" if bp is None else f"{bp:.3f}"
                r["settled_at_utc"] = iso(now)
                newly_settled += 1
                if up is None:
                    append_note(r, "Marathonbet price was not observed at first crossing; excluded from user ROI")
        elif st == "CANC":
            r["settlement_status"] = "VOID"
            r["result"] = "VOID"
            r["settled_at_utc"] = iso(now)
            up = profit("VOID", r.get("user_cross_odds"))
            bp = profit("VOID", r.get("bet365_cross_odds"))
            r["user_profit_u"] = "" if up is None else f"{up:.3f}"
            r["bet365_profit_u"] = "" if bp is None else f"{bp:.3f}"
        elif st in {"ABD", "AWD", "WO"}:
            r["settlement_status"] = "REVIEW"
            r["result"] = "REVIEW"
            append_note(r, f"Non-standard fixture status {st}; no automatic P/L")

    rows.sort(key=lambda r: (r.get("crossed_at_utc") or "", r.get("watch_id") or ""))
    write_csv(LEDGER, rows)

    overall = metric(rows)
    groups = defaultdict(list)
    for r in rows:
        family = r.get("watch_family") or r.get("source_stage") or "UNKNOWN"
        if r.get("source_stage") == "Stage63":
            family = f"{family} — {r.get('selection_display') or ''}"
        groups[family].append(r)
    by_family = {k: metric(v) for k, v in sorted(groups.items())}

    payload = {
        "generated_at_utc": iso(now),
        "status": "OK",
        "scope": "prospective research WATCH crossings only",
        "overall": overall,
        "by_family": by_family,
        "policy": {
            "stake": "flat 1u measurement only",
            "user_execution": "Marathonbet price captured at first crossing",
            "alternative_market_selection": "forbidden after crossing/result",
            "close_comparison": "first-crossing sample retained; later qualification/reversion measured separately",
            "historical_backfill": "forbidden",
            "canonical_forward": "unchanged",
        },
        "warnings": warnings,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# PBK WATCH Performance",
        "",
        f"Generated UTC: {iso(now)}",
        "Scope: только prospective WATCH; это не реальные ставки и не canonical R1/R2/R3.",
        "",
        "## Overall",
        f"- Crossing events: {overall['crossings']} | pending {overall['pending']} | settled {overall['settled']} | void {overall['void']} | review {overall['review']}",
        f"- Marathonbet price coverage at crossing: {fmt(overall['user_execution_coverage_pct'], '%')} ({overall['user_price_rows']}/{overall['crossings']})",
        f"- First-crossing paper P&L: {overall['user_profit_u']:.3f}u | ROI {fmt(overall['user_roi_pct'], '%')} | W-L {overall['wins']}-{overall['losses']}",
        f"- Close observed: {overall['close_observed']} | stayed qualified {overall['close_qualified']} | reverted {overall['reverted_at_close']} | persistence {fmt(overall['close_persistence_pct'], '%')}",
        f"- Close-qualified subset: settled {overall['close_qualified_settled']} | P&L {overall['close_qualified_profit_u']:.3f}u | ROI {fmt(overall['close_qualified_roi_pct'], '%')}",
        f"- Reverted subset: settled {overall['reverted_settled']} | P&L {overall['reverted_profit_u']:.3f}u | ROI {fmt(overall['reverted_roi_pct'], '%')}",
        f"- Observed max drawdown: {fmt(overall['observed_max_drawdown_u'], 'u')}",
        "",
    ]
    for name, m in by_family.items():
        md += [
            f"## {name}",
            f"- Crossings: {m['crossings']} | pending {m['pending']} | settled {m['settled']}",
            f"- Marathonbet coverage: {fmt(m['user_execution_coverage_pct'], '%')}",
            f"- First-crossing P&L: {m['user_profit_u']:.3f}u | ROI {fmt(m['user_roi_pct'], '%')} | W-L {m['wins']}-{m['losses']}",
            f"- Close persistence: {fmt(m['close_persistence_pct'], '%')} ({m['close_qualified']}/{m['close_observed']})",
            f"- Close-qualified ROI: {fmt(m['close_qualified_roi_pct'], '%')} | Reverted ROI: {fmt(m['reverted_roi_pct'], '%')}",
            "",
        ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    meta = {
        "run_at_utc": iso(now),
        "status": "OK",
        "new_watch_rows": new_rows,
        "newly_settled_rows": newly_settled,
        "fixture_api_calls": fixture_calls,
        "total_crossings": overall["crossings"],
        "settled": overall["settled"],
        "pending": overall["pending"],
        "user_execution_coverage_pct": overall["user_execution_coverage_pct"],
        "user_roi_pct": overall["user_roi_pct"],
        "warnings": warnings,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
