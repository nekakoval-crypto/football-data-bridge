#!/usr/bin/env python3
"""Append Stage62 Bundesliga O/U research WATCH to Stage58 daily brief.

Presentation only. Never mutates canonical forward, signals, prices or strategy
eligibility. Stage62 remains explicitly separate from R1/R2/R3.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
BRIEF_JSON = OPS / "daily_brief.json"
BRIEF_MD = OPS / "daily_brief.md"
META = OPS / "stage62_last_run.json"
OPENERS = OPS / "stage62_ou_openers.csv"
CROSSINGS = OPS / "stage62_ou_crossings.csv"
CLOSES = OPS / "stage62_ou_closes.csv"


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        return float(str(x).strip())
    except Exception:
        return None


def pct_text(x):
    v = fnum(x)
    return "N/A" if v is None else f"{v*100:+.2f} pp"


def main():
    if not BRIEF_JSON.exists() or not BRIEF_MD.exists():
        print("Stage62 brief adapter: Stage58 brief missing; nothing to append")
        return

    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    openers = read_csv(OPENERS)
    crossings = read_csv(CROSSINGS)
    closes = read_csv(CLOSES)
    closed_ids = {r.get("api_fixture_id") for r in closes if r.get("api_fixture_id")}
    active_crossings = [r for r in crossings if r.get("api_fixture_id") not in closed_ids]
    qualified_closes = [r for r in closes if r.get("o1_close_qualified") == "YES"]

    watch = {
        "status": "WATCH_ONLY_NOT_CANONICAL_RULE",
        "scope": "Bundesliga Over 2.5 Steam O1",
        "definition": "Bet365 no-vig P(Over 2.5) rises by >=3pp from frozen opener to observed close",
        "canonical_forward_changed": False,
        "tracked_openers": len(openers),
        "active_crossings": len(active_crossings),
        "total_crossings": len(crossings),
        "observed_closes": len(closes),
        "close_qualified_total": len(qualified_closes),
        "user_bookmaker": meta.get("user_bookmaker") or "Marathonbet",
        "latest_run_utc": meta.get("run_at_utc") or "",
        "warnings": meta.get("warnings") or [],
        "crossings": [
            {
                "fixture_id": r.get("api_fixture_id") or "",
                "home_team": r.get("home_team") or "",
                "away_team": r.get("away_team") or "",
                "movement_pp": r.get("movement_pp") or "",
                "crossed_at_utc": r.get("crossed_at_utc") or "",
                "minutes_to_kickoff": r.get("minutes_to_kickoff") or "",
                "bet365_over25": r.get("bet365_cross_over25") or "",
                "user_over25": r.get("user_cross_over25") or "",
                "note": "WATCH only; not a canonical bet",
            }
            for r in active_crossings[-10:]
        ],
        "recent_close_qualified": [
            {
                "fixture_id": r.get("api_fixture_id") or "",
                "home_team": r.get("home_team") or "",
                "away_team": r.get("away_team") or "",
                "movement_pp": r.get("movement_pp") or "",
                "close_gap_minutes": r.get("close_gap_minutes") or "",
                "bet365_close_over25": r.get("bet365_close_over25") or "",
                "user_close_over25": r.get("user_close_over25") or "",
            }
            for r in qualified_closes[-5:]
        ],
    }

    payload = json.loads(BRIEF_JSON.read_text(encoding="utf-8"))
    payload["ou_steam_watch"] = watch
    BRIEF_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = BRIEF_MD.read_text(encoding="utf-8").rstrip()
    block = [
        "",
        "---",
        "",
        "# O/U STEAM WATCH — research only",
        "",
        "> This is **not a canonical rule and not a bet signal**. R1/R2/R3 are unchanged.",
        "",
        "- Scope: Bundesliga Over 2.5 Steam O1 (+3 pp no-vig from frozen Bet365 O/U 2.5 opener).",
        f"- Frozen O/U openers tracked: {len(openers)}",
        f"- Active +3 pp Over crossings: {len(active_crossings)}",
        f"- Observed closes: {len(closes)} | Close-qualified O1 watches: {len(qualified_closes)}",
        f"- Executable bookmaker being observed: {watch['user_bookmaker']}",
    ]

    if active_crossings:
        block += ["", "## Current O/U crossings"]
        for r in active_crossings[-10:]:
            block.append(
                f"- WATCH | {r.get('home_team')} — {r.get('away_team')} | "
                f"Over move {pct_text(r.get('movement_pp'))} | "
                f"Bet365 O2.5 {r.get('bet365_cross_over25') or 'N/A'} | "
                f"{watch['user_bookmaker']} O2.5 {r.get('user_cross_over25') or 'NO_PRICE'} | "
                f"{r.get('minutes_to_kickoff') or 'N/A'} min to kickoff"
            )
    else:
        block += ["", "- No active +3 pp Over crossing is currently recorded."]

    if qualified_closes:
        block += ["", "## Recent close-qualified O/U watches"]
        for r in qualified_closes[-5:]:
            block.append(
                f"- {r.get('home_team')} — {r.get('away_team')} | "
                f"move {pct_text(r.get('movement_pp'))} | "
                f"B365 close O2.5 {r.get('bet365_close_over25') or 'N/A'} | "
                f"{watch['user_bookmaker']} close O2.5 {r.get('user_close_over25') or 'NO_PRICE'}"
            )

    BRIEF_MD.write_text(md + "\n" + "\n".join(block) + "\n", encoding="utf-8")
    print(json.dumps({
        "stage62_watch_appended": True,
        "tracked_openers": len(openers),
        "active_crossings": len(active_crossings),
        "close_qualified": len(qualified_closes),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
