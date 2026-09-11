#!/usr/bin/env python3
"""Stage 60: clean prospective PBK forward-performance summary.

Consumes only the canonical prospective forward and the Stage59 executable
paper ledger. Historical backtest rows are never introduced here.
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
VIEW = OPS / "user_forward_view.csv"
OUT_JSON = OPS / "forward_performance.json"
OUT_MD = OPS / "forward_performance.md"
META = OPS / "stage60_last_run.json"


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fnum(v):
    try:
        x = float(str(v).strip())
        return x if math.isfinite(x) else None
    except Exception:
        return None


def metrics(rows):
    total = len(rows)
    pending = sum(1 for r in rows if r.get("status") in {"PAPER", "OPEN", "REVIEW"})
    settled = sum(1 for r in rows if r.get("status") == "SETTLED")
    void = sum(1 for r in rows if r.get("status") == "VOID")
    frozen = sum(1 for r in rows if r.get("user_execution_status") == "FROZEN")

    user_settled = []
    market_settled = []
    clv_values = []
    wins = losses = 0
    for r in rows:
        if r.get("status") == "SETTLED":
            up = fnum(r.get("user_profit_u"))
            stake = fnum(r.get("stake_u")) or 1.0
            if up is not None:
                user_settled.append((stake, up, r))
                if up > 0:
                    wins += 1
                elif up < 0:
                    losses += 1
            mp = fnum(r.get("market_profit_u"))
            if mp is not None:
                market_settled.append((stake, mp, r))
        c = fnum(r.get("user_price_ratio_clv_pct"))
        if c is not None:
            clv_values.append(c)

    user_stake = sum(x[0] for x in user_settled)
    user_profit = sum(x[1] for x in user_settled)
    market_stake = sum(x[0] for x in market_settled)
    market_profit = sum(x[1] for x in market_settled)

    # Observed drawdown only; no extrapolation or theoretical maximum.
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    ordered = sorted(user_settled, key=lambda x: (x[2].get("kickoff_utc") or "", x[2].get("forward_id") or ""))
    for _, p, _ in ordered:
        equity += p
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    return {
        "rows": total,
        "pending_rows": pending,
        "settled_rows": settled,
        "void_rows": void,
        "frozen_user_execution_rows": frozen,
        "user_execution_coverage_pct": round((100.0 * frozen / total), 3) if total else None,
        "settled_with_user_execution": len(user_settled),
        "wins": wins,
        "losses": losses,
        "user_settled_stake_u": round(user_stake, 3),
        "user_profit_u": round(user_profit, 3),
        "user_roi_pct": round(100.0 * user_profit / user_stake, 3) if user_stake else None,
        "market_settled_stake_u": round(market_stake, 3),
        "market_profit_u": round(market_profit, 3),
        "market_roi_pct": round(100.0 * market_profit / market_stake, 3) if market_stake else None,
        "user_close_rows": len(clv_values),
        "avg_user_price_ratio_clv_pct": round(sum(clv_values) / len(clv_values), 3) if clv_values else None,
        "observed_user_max_drawdown_u": round(max_dd, 3) if user_settled else None,
    }


def fmt(v, suffix=""):
    return "N/A" if v is None else f"{v}{suffix}"


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = read_csv(VIEW)
    overall = metrics(rows)

    groups = defaultdict(list)
    for r in rows:
        groups[r.get("rule") or "UNKNOWN"].append(r)
    by_rule = {rule: metrics(rr) for rule, rr in sorted(groups.items())}

    payload = {
        "generated_at_utc": now,
        "status": "OK",
        "scope": "clean prospective canonical forward only",
        "overall": overall,
        "by_rule": by_rule,
        "policy": {
            "user_roi": "frozen Stage59 paper-user execution from allowlisted bookmaker",
            "market_roi": "canonical Stage53 market-best execution retained separately",
            "clv": "paper-user execution / observed user close - 1, same selection",
            "drawdown": "observed settled forward only; never theoretical",
            "historical_backfill": "forbidden",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# PBK Forward Performance",
        "",
        f"Generated UTC: {now}",
        "Scope: clean prospective canonical forward only; no historical backfill.",
        "",
        "## Overall",
        f"- Rows: {overall['rows']} | pending {overall['pending_rows']} | settled {overall['settled_rows']} | void {overall['void_rows']}",
        f"- Executable-price coverage: {fmt(overall['user_execution_coverage_pct'], '%')} ({overall['frozen_user_execution_rows']}/{overall['rows']})",
        f"- User paper P&L: {overall['user_profit_u']:.3f}u on {overall['user_settled_stake_u']:.3f}u settled stake | ROI {fmt(overall['user_roi_pct'], '%')}",
        f"- Market paper P&L: {overall['market_profit_u']:.3f}u on {overall['market_settled_stake_u']:.3f}u settled stake | ROI {fmt(overall['market_roi_pct'], '%')}",
        f"- User CLV rows: {overall['user_close_rows']} | avg price-ratio CLV {fmt(overall['avg_user_price_ratio_clv_pct'], '%')}",
        f"- Observed user max drawdown: {fmt(overall['observed_user_max_drawdown_u'], 'u')}",
        "",
    ]
    for rule, m in by_rule.items():
        md += [
            f"## {rule}",
            f"- Rows: {m['rows']} | pending {m['pending_rows']} | settled {m['settled_rows']} | void {m['void_rows']}",
            f"- Executable-price coverage: {fmt(m['user_execution_coverage_pct'], '%')}",
            f"- User paper P&L: {m['user_profit_u']:.3f}u | ROI {fmt(m['user_roi_pct'], '%')} | W-L {m['wins']}-{m['losses']}",
            f"- Avg user price-ratio CLV: {fmt(m['avg_user_price_ratio_clv_pct'], '%')}",
            "",
        ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    meta = {
        "run_at_utc": now,
        "status": "OK",
        "forward_rows": overall["rows"],
        "settled_rows": overall["settled_rows"],
        "user_execution_coverage_pct": overall["user_execution_coverage_pct"],
        "user_roi_pct": overall["user_roi_pct"],
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
