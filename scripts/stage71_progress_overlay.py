#!/usr/bin/env python3
"""Stage 71L — live challenger progress overlay.

Adds user-facing progress metrics to the final Stage71 challenger board without
changing eligibility, promotion, suspension, stakes, or canonical scope.
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
BOARD = OPS / "stage71_challenger_board.csv"
FORWARD = OPS / "stage71_challenger_forward.csv"
USER_FORWARD = OPS / "user_forward_view.csv"
OUT_JSON = OPS / "stage71_challenger_board.json"
OUT_MD = OPS / "stage71_challenger_board.md"
META = OPS / "stage71_last_run.json"

REVIEW_TARGET = 60
DISCOVERY_TARGET = 120

ADDED_FIELDS = [
    "prospective_captured",
    "prospective_executable",
    "prospective_pending_executable",
    "review_target_settled",
    "review_remaining_settled",
    "review_progress_pct",
    "discovery_target_settled",
    "discovery_remaining_settled",
    "discovery_progress_pct",
    "progress_path",
]


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
    priced = [
        r for r in rows
        if fnum(r.get("user_odds") or r.get("user_cross_odds") or r.get("paper_user_execution_odds")) is not None
    ]
    settled = [
        r for r in priced
        if str(r.get("status") or r.get("settlement_status") or "").upper() == "SETTLED"
        and fnum(r.get("user_profit_u")) is not None
    ]
    settled.sort(
        key=lambda r: (
            r.get("kickoff_utc") or "",
            r.get("research_id") or r.get("forward_id") or r.get("watch_id") or "",
        )
    )
    cut = len(settled) // 2
    first, second = settled[:cut], settled[cut:]
    return {
        "captured": len(rows),
        "executable": len(priced),
        "pending_executable": max(0, len(priced) - len(settled)),
        "coverage": 100.0 * len(priced) / len(rows) if rows else None,
        "settled": len(settled),
        "roi": roi(settled),
        "first_roi": roi(first),
        "second_roi": roi(second),
    }


def fmt_num(v, digits=1):
    if v in (None, ""):
        return "—"
    try:
        return f"{float(v):.{digits}f}"
    except Exception:
        return str(v)


def progress_path(status):
    s = str(status or "").upper()
    if s in {"ACTIVE", "DEGRADATION_REVIEW", "SUSPENSION_REVIEW"}:
        return "ACTIVE_FORWARD_MONITORING"
    if s in {"CHALLENGER", "REVIEW_ELIGIBLE"}:
        return "HISTORICAL_CHALLENGER_PROMOTION"
    if s in {"DATA_REQUIRED", "MONITORING", "REGIME_DISCOVERY_ELIGIBLE"}:
        return "REGIME_DISCOVERY"
    if s == "MONITORING_REJECTED_CURRENT_RULE":
        return "REJECTED_CURRENT_RULE_RESEARCH_ONLY"
    return "OTHER"


def progress_reason(row, m):
    status = str(row.get("status") or "")
    old = str(row.get("blocking_reason") or "").strip()
    cov = fmt_num(m["coverage"], 1)
    total_roi = fmt_num(m["roi"], 2)
    first_roi = fmt_num(m["first_roi"], 2)
    second_roi = fmt_num(m["second_roi"], 2)

    if status == "REVIEW_ELIGIBLE":
        return "all locked historical + prospective gates passed; human review required; no automatic promotion"
    if status == "REGIME_DISCOVERY_ELIGIBLE":
        return "120-bet discovery gate passed; requires new preregistration and a fresh future holdout; discovery sample cannot be reused"
    if status in {"ACTIVE", "DEGRADATION_REVIEW", "SUSPENSION_REVIEW"}:
        if m["settled"] < REVIEW_TARGET:
            return (
                f"active forward sample {m['settled']}/{REVIEW_TARGET} settled "
                f"({REVIEW_TARGET - m['settled']} remaining before deterioration review can be evaluated)"
            )
        return old or "active forward monitoring"
    if status == "CHALLENGER":
        return (
            f"promotion sample {m['settled']}/{REVIEW_TARGET} settled "
            f"({max(0, REVIEW_TARGET - m['settled'])} remaining); "
            f"executable {m['executable']}/{m['captured']}; Marathonbet coverage {cov}%; "
            f"ROI {total_roi}%; first-half {first_roi}%; second-half {second_roi}%; "
            "human review only after all locked gates pass"
        )
    if status == "MONITORING":
        return (
            f"fresh discovery sample {m['settled']}/{DISCOVERY_TARGET} settled "
            f"({max(0, DISCOVERY_TARGET - m['settled'])} remaining); "
            f"executable {m['executable']}/{m['captured']}; Marathonbet coverage {cov}%; "
            f"ROI {total_roi}%; first-half {first_roi}%; second-half {second_roi}%; "
            "no direct promotion"
        )
    if status == "DATA_REQUIRED":
        return (
            "comparable historical evidence missing; "
            f"prospective discovery {m['settled']}/{DISCOVERY_TARGET} settled; "
            f"captured {m['captured']}, executable {m['executable']}; no direct promotion"
        )
    if status == "MONITORING_REJECTED_CURRENT_RULE":
        return old or "unchanged historical transfer rejected; research monitoring does not restore canonical eligibility"
    return old


def group_rows():
    research = defaultdict(list)
    for r in read_csv(FORWARD):
        fam, league = r.get("family") or "", r.get("league") or ""
        if fam and league:
            research[(fam, league)].append(r)

    canonical = defaultdict(list)
    for r in read_csv(USER_FORWARD):
        fam = r.get("rule") or ""
        if fam not in {"R1", "R2"}:
            continue
        league = r.get("league") or "Serie A"
        canonical[(fam, league)].append(r)
    return research, canonical


def validate(rows):
    seen = set()
    for r in rows:
        key = (r.get("family"), r.get("league"))
        if key in seen:
            raise RuntimeError(f"duplicate challenger-board row: {key}")
        seen.add(key)

        captured = int(r.get("prospective_captured") or 0)
        executable = int(r.get("prospective_executable") or 0)
        settled = int(r.get("prospective_settled") or 0)
        if not (0 <= settled <= executable <= captured):
            raise RuntimeError(
                f"invalid progress counts for {key}: captured={captured}, executable={executable}, settled={settled}"
            )
        for name in ("review_progress_pct", "discovery_progress_pct"):
            v = fnum(r.get(name))
            if v is None or not (0.0 <= v <= 100.0):
                raise RuntimeError(f"invalid {name} for {key}: {r.get(name)}")


def main():
    rows = read_csv(BOARD)
    if not rows:
        raise SystemExit("Stage71 board missing or empty")

    research, canonical = group_rows()

    for r in rows:
        key = (r.get("family") or "", r.get("league") or "")
        active = str(r.get("status") or "") in {"ACTIVE", "DEGRADATION_REVIEW", "SUSPENSION_REVIEW"}
        source_rows = canonical.get(key, []) if active else research.get(key, [])
        m = metrics(source_rows)

        r["prospective_captured"] = str(m["captured"])
        r["prospective_executable"] = str(m["executable"])
        r["prospective_pending_executable"] = str(m["pending_executable"])
        r["prospective_settled"] = str(m["settled"])
        r["prospective_roi_pct"] = "" if m["roi"] is None else f"{m['roi']:.3f}"
        r["prospective_first_half_roi_pct"] = "" if m["first_roi"] is None else f"{m['first_roi']:.3f}"
        r["prospective_second_half_roi_pct"] = "" if m["second_roi"] is None else f"{m['second_roi']:.3f}"
        r["marathonbet_coverage_pct"] = "" if m["coverage"] is None else f"{m['coverage']:.3f}"

        r["review_target_settled"] = str(REVIEW_TARGET)
        r["review_remaining_settled"] = str(max(0, REVIEW_TARGET - m["settled"]))
        r["review_progress_pct"] = f"{min(100.0, 100.0 * m['settled'] / REVIEW_TARGET):.1f}"
        r["discovery_target_settled"] = str(DISCOVERY_TARGET)
        r["discovery_remaining_settled"] = str(max(0, DISCOVERY_TARGET - m["settled"]))
        r["discovery_progress_pct"] = f"{min(100.0, 100.0 * m['settled'] / DISCOVERY_TARGET):.1f}"
        r["progress_path"] = progress_path(r.get("status"))
        r["blocking_reason"] = progress_reason(r, m)

    validate(rows)

    original_fields = list(rows[0].keys())
    fields = original_fields + [f for f in ADDED_FIELDS if f not in original_fields]
    with BOARD.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    payload = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {}
    payload["rows"] = rows
    payload["progress_policy"] = {
        "captured_definition": "qualifying frozen family×league research/canonical rows",
        "executable_definition": "rows with a captured user-accessible execution price",
        "settled_definition": "executable rows with final settlement and user_profit_u",
        "historical_challenger_review_target": REVIEW_TARGET,
        "regime_discovery_target": DISCOVERY_TARGET,
        "marathonbet_min_coverage_pct": 90,
        "automatic_promotion": "FORBIDDEN",
        "automatic_suspension": "FORBIDDEN",
    }
    payload["progress_generated_at_utc"] = now_iso()
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    leaders = {
        fam: next((r.get("league") for r in rows if r.get("family") == fam and r.get("leader") == "YES"), "нет")
        for fam in ("R1", "R2")
    }
    md = [
        "# PBK Stage71 — League & Market Challenger Board",
        "",
        f"Обновлено UTC: {payload['progress_generated_at_utc']}",
        f"Текущие лидеры R1/R2: {leaders['R1']} / {leaders['R2']}",
        "",
        "> Captured → executable → settled — это исследовательский прогресс. Он не меняет canonical eligibility и не создаёт автоматический promotion.",
        "",
    ]
    for fam in ("R1", "R2"):
        md += [
            f"## {fam}",
            "",
            "| Лига | Статус | Captured | Executable | Settled | Mbet cov. | ROI | 1H ROI | 2H ROI | До 60 | До 120 |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in [x for x in rows if x.get("family") == fam]:
            star = " 🏆" if r.get("leader") == "YES" else ""
            md.append(
                f"| {r.get('league')}{star} | {r.get('status')} | {r.get('prospective_captured')} | "
                f"{r.get('prospective_executable')} | {r.get('prospective_settled')} | "
                f"{fmt_num(r.get('marathonbet_coverage_pct'), 1)} | {fmt_num(r.get('prospective_roi_pct'), 2)} | "
                f"{fmt_num(r.get('prospective_first_half_roi_pct'), 2)} | {fmt_num(r.get('prospective_second_half_roi_pct'), 2)} | "
                f"{r.get('review_remaining_settled')} | {r.get('discovery_remaining_settled')} |"
            )
        md.append("")

    md += [
        "## Locked gates",
        f"- Historical challenger → REVIEW_ELIGIBLE: минимум {REVIEW_TARGET} settled executable + Marathonbet coverage >=90% + положительный ROI целиком и в обеих хронологических половинах.",
        f"- Regime discovery: минимум {DISCOVERY_TARGET} fresh settled executable + те же coverage/ROI требования; затем только новая preregistration и новый будущий holdout.",
        "- Никакого автоматического promotion, suspension или изменения 1u.",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    meta["progress_overlay_at_utc"] = payload["progress_generated_at_utc"]
    meta["progress_rows"] = len(rows)
    meta["progress_extended_rows"] = sum(1 for r in rows if r.get("group") == "EXTENDED")
    meta["progress_with_captured"] = sum(1 for r in rows if int(r.get("prospective_captured") or 0) > 0)
    meta["progress_with_settled"] = sum(1 for r in rows if int(r.get("prospective_settled") or 0) > 0)
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "rows": len(rows),
        "with_captured": meta["progress_with_captured"],
        "with_settled": meta["progress_with_settled"],
        "review_target": REVIEW_TARGET,
        "discovery_target": DISCOVERY_TARGET,
        "status": "OK",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
