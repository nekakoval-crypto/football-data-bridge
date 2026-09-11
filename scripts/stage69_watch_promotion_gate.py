#!/usr/bin/env python3
"""Stage 69 — preregistered WATCH promotion gate.

Read-only classifier over Stage65 prospective rows. It never creates or edits
canonical R-rules. Stage61/62 may become REVIEW_ELIGIBLE only after the locked
criteria are met. Stage63 is discovery-only and can never directly promote.
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
LEDGER = OPS / "stage65_watch_ledger.csv"
OUT_JSON = OPS / "watch_promotion_gate.json"
OUT_MD = OPS / "watch_promotion_gate.md"
META = OPS / "stage69_last_run.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def roi(rows):
    vals = [fnum(r.get("user_profit_u")) for r in rows]
    vals = [x for x in vals if x is not None]
    return (100.0 * sum(vals) / len(vals)) if vals else None


def metrics(rows):
    crossings = len(rows)
    user_price_rows = [r for r in rows if fnum(r.get("user_cross_odds")) is not None]
    exec_settled = [
        r for r in rows
        if r.get("settlement_status") == "SETTLED"
        and fnum(r.get("user_cross_odds")) is not None
        and fnum(r.get("user_profit_u")) is not None
    ]
    ordered = sorted(exec_settled, key=lambda r: (r.get("kickoff_utc") or "", r.get("watch_id") or ""))
    cut = len(ordered) // 2
    first = ordered[:cut]
    second = ordered[cut:]
    close_obs_settled = [r for r in exec_settled if r.get("close_observed") == "YES"]
    close_q = [r for r in close_obs_settled if r.get("close_qualified") == "YES"]
    return {
        "crossings": crossings,
        "user_price_rows": len(user_price_rows),
        "execution_coverage_pct": round(100.0 * len(user_price_rows) / crossings, 3) if crossings else None,
        "settled_executable": len(exec_settled),
        "roi_pct": round(roi(exec_settled), 3) if roi(exec_settled) is not None else None,
        "first_half_n": len(first),
        "first_half_roi_pct": round(roi(first), 3) if roi(first) is not None else None,
        "second_half_n": len(second),
        "second_half_roi_pct": round(roi(second), 3) if roi(second) is not None else None,
        "close_observed_settled": len(close_obs_settled),
        "close_observed_coverage_pct": round(100.0 * len(close_obs_settled) / len(exec_settled), 3) if exec_settled else None,
        "close_qualified_settled": len(close_q),
        "close_qualified_roi_pct": round(roi(close_q), 3) if roi(close_q) is not None else None,
    }


def gate_stage61_62(m):
    reasons = []
    if m["settled_executable"] < 60:
        reasons.append(f"settled {m['settled_executable']}/60")
    if m["execution_coverage_pct"] is None or m["execution_coverage_pct"] < 90:
        reasons.append(f"Marathonbet coverage {m['execution_coverage_pct']}% <90%")
    if m["roi_pct"] is None or m["roi_pct"] <= 0:
        reasons.append(f"ROI {m['roi_pct']} not >0")
    if m["first_half_roi_pct"] is None or m["first_half_roi_pct"] <= 0:
        reasons.append(f"first-half ROI {m['first_half_roi_pct']} not >0")
    if m["second_half_roi_pct"] is None or m["second_half_roi_pct"] <= 0:
        reasons.append(f"second-half ROI {m['second_half_roi_pct']} not >0")
    if m["close_observed_coverage_pct"] is None or m["close_observed_coverage_pct"] < 90:
        reasons.append(f"close coverage {m['close_observed_coverage_pct']}% <90%")
    if m["close_qualified_settled"] < 20:
        reasons.append(f"close-qualified subset {m['close_qualified_settled']}/20")
    elif m["close_qualified_roi_pct"] is None or m["close_qualified_roi_pct"] < 0:
        reasons.append(f"close-qualified ROI {m['close_qualified_roi_pct']} <0")

    if not reasons:
        return "REVIEW_ELIGIBLE", []
    if (
        m["settled_executable"] >= 60
        and (m["execution_coverage_pct"] or 0) >= 90
        and (m["roi_pct"] or 0) > 0
        and (m["first_half_roi_pct"] or 0) > 0
        and (m["second_half_roi_pct"] or 0) > 0
        and (m["close_observed_coverage_pct"] or 0) >= 90
        and m["close_qualified_settled"] < 20
    ):
        return "COLLECTING_CLOSE_SUBSET", reasons
    return "COLLECTING", reasons


def main():
    now = now_iso()
    rows = read_csv(LEDGER)
    by_stage = defaultdict(list)
    for r in rows:
        by_stage[r.get("source_stage") or "UNKNOWN"].append(r)

    result = {}
    for stage in ("Stage61", "Stage62", "Stage63"):
        rr = by_stage.get(stage, [])
        m = metrics(rr)
        if stage == "Stage63":
            status = "DISCOVERY_ONLY_NO_DIRECT_PROMOTION"
            reasons = ["No historical BTTS first/close dataset; any finding needs a new preregistration and fresh holdout."]
        else:
            status, reasons = gate_stage61_62(m)
        result[stage] = {
            "status": status,
            "metrics": m,
            "blocking_reasons": reasons,
        }

    payload = {
        "generated_at_utc": now,
        "status": "OK",
        "policy_locked_at": "2026-09-11",
        "families": result,
        "automatic_promotion": "FORBIDDEN",
        "policy": {
            "stage61_stage62_review_min_settled": 60,
            "min_marathonbet_coverage_pct": 90,
            "overall_roi_must_be_positive": True,
            "chronological_both_halves_roi_must_be_positive": True,
            "close_observed_coverage_min_pct": 90,
            "close_qualified_min_settled": 20,
            "close_qualified_roi_must_be_nonnegative": True,
            "stage63": "discovery only; requires new preregistration + fresh holdout before any R-rule proposal",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# PBK WATCH Promotion Gate",
        "",
        f"Обновлено UTC: {now}",
        "Никакой WATCH не может автоматически стать R-правилом.",
        "",
    ]
    for stage in ("Stage61", "Stage62", "Stage63"):
        x = result[stage]
        m = x["metrics"]
        md += [
            f"## {stage} — {x['status']}",
            f"- Crossings: {m['crossings']} | settled executable: {m['settled_executable']}",
            f"- Marathonbet coverage: {m['execution_coverage_pct'] if m['execution_coverage_pct'] is not None else 'N/A'}%",
            f"- ROI: {m['roi_pct'] if m['roi_pct'] is not None else 'N/A'}%",
            f"- Chronological halves ROI: {m['first_half_roi_pct'] if m['first_half_roi_pct'] is not None else 'N/A'}% / {m['second_half_roi_pct'] if m['second_half_roi_pct'] is not None else 'N/A'}%",
            f"- Close coverage: {m['close_observed_coverage_pct'] if m['close_observed_coverage_pct'] is not None else 'N/A'}%",
            f"- Close-qualified: {m['close_qualified_settled']} settled | ROI {m['close_qualified_roi_pct'] if m['close_qualified_roi_pct'] is not None else 'N/A'}%",
        ]
        if x["blocking_reasons"]:
            md.append("- Blocking: " + "; ".join(x["blocking_reasons"]))
        md.append("")

    md += [
        "> `REVIEW_ELIGIBLE` означает только право на отдельный locked review. Это не автоматическое создание R4/R5.",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    META.write_text(json.dumps({
        "run_at_utc": now,
        "status": "OK",
        "stage61_gate": result["Stage61"]["status"],
        "stage62_gate": result["Stage62"]["status"],
        "stage63_gate": result["Stage63"]["status"],
        "api_calls": 0,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({k: result[k]["status"] for k in result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
