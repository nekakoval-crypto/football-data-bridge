#!/usr/bin/env python3
"""Append compact Stage65 WATCH performance status to the Daily Brief.

Presentation only. Never changes canonical signals, WATCH events or settlement.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
BRIEF_JSON = OPS / "daily_brief.json"
BRIEF_MD = OPS / "daily_brief.md"
PERF = OPS / "watch_performance.json"


def fmt(v, suffix=""):
    return "N/A" if v is None else f"{v}{suffix}"


def main():
    if not BRIEF_JSON.exists() or not BRIEF_MD.exists() or not PERF.exists():
        print("Stage65 brief adapter: required files missing; nothing to append")
        return

    perf = json.loads(PERF.read_text(encoding="utf-8"))
    overall = perf.get("overall") or {}
    by_family = perf.get("by_family") or {}

    brief = json.loads(BRIEF_JSON.read_text(encoding="utf-8"))
    brief["watch_performance"] = perf
    BRIEF_JSON.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    md = BRIEF_MD.read_text(encoding="utf-8").rstrip()
    block = [
        "",
        "---",
        "",
        "# WATCH PERFORMANCE — prospective only",
        "",
        "> Это paper-оценка research WATCH, а не реальные ставки и не R1/R2/R3.",
        "",
        f"- Crossings: {overall.get('crossings', 0)} | settled {overall.get('settled', 0)} | pending {overall.get('pending', 0)}",
        f"- Marathonbet coverage at crossing: {fmt(overall.get('user_execution_coverage_pct'), '%')}",
        f"- First-crossing P&L: {overall.get('user_profit_u', 0):.3f}u | ROI {fmt(overall.get('user_roi_pct'), '%')} | W-L {overall.get('wins', 0)}-{overall.get('losses', 0)}",
        f"- Close: observed {overall.get('close_observed', 0)} | stayed qualified {overall.get('close_qualified', 0)} | reverted {overall.get('reverted_at_close', 0)} | persistence {fmt(overall.get('close_persistence_pct'), '%')}",
        f"- Close-qualified ROI: {fmt(overall.get('close_qualified_roi_pct'), '%')} | Reverted ROI: {fmt(overall.get('reverted_roi_pct'), '%')}",
    ]

    if by_family:
        block += ["", "## By WATCH family"]
        for name, m in by_family.items():
            block.append(
                f"- {name}: crossings {m.get('crossings', 0)}, settled {m.get('settled', 0)}, "
                f"ROI {fmt(m.get('user_roi_pct'), '%')}, close persistence {fmt(m.get('close_persistence_pct'), '%')}"
            )
    else:
        block += ["", "- WATCH crossings пока нет — статистика начнётся с первого prospectively recorded события."]

    BRIEF_MD.write_text(md + "\n" + "\n".join(block) + "\n", encoding="utf-8")
    print(json.dumps({
        "stage65_watch_performance_appended": True,
        "crossings": overall.get("crossings", 0),
        "settled": overall.get("settled", 0),
        "roi_pct": overall.get("user_roi_pct"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
