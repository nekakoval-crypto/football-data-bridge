#!/usr/bin/env python3
"""Append Stage61 research WATCH status to the Stage58 human-readable brief.

Presentation only. Never mutates canonical forward, signals, prices or strategy
eligibility. Stage61 remains explicitly separate from R1/R2/R3.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
BRIEF_JSON = OPS / "daily_brief.json"
BRIEF_MD = OPS / "daily_brief.md"
S61_META = OPS / "stage61_last_run.json"
OPENERS = OPS / "stage61_market_openers.csv"
CROSSINGS = OPS / "stage61_market_crossings.csv"
CLOSES = OPS / "stage61_market_closes.csv"


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
        print("Stage61 brief adapter: Stage58 brief missing; nothing to append")
        return

    meta = {}
    if S61_META.exists():
        meta = json.loads(S61_META.read_text(encoding="utf-8"))
    openers = read_csv(OPENERS)
    crossings = read_csv(CROSSINGS)
    closes = read_csv(CLOSES)
    closed_ids = {r.get("api_fixture_id") for r in closes if r.get("api_fixture_id")}
    active_crossings = [r for r in crossings if r.get("api_fixture_id") not in closed_ids]
    qualified_closes = [r for r in closes if r.get("m1_close_qualified") == "YES"]

    watch = {
        "status": "WATCH_ONLY_NOT_CANONICAL_R4",
        "scope": "Premier League Favorite Steam M1",
        "definition": "same opening favorite remains favorite; no-vig probability +3pp by observed close",
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
                "opening_favorite": r.get("opening_favorite") or "",
                "movement_pp": r.get("movement_pp") or "",
                "crossed_at_utc": r.get("crossed_at_utc") or "",
                "minutes_to_kickoff": r.get("minutes_to_kickoff") or "",
                "bet365_cross_odds": r.get("bet365_cross_odds") or "",
                "user_cross_odds": r.get("user_cross_odds") or "",
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
                "bet365_close_favorite_odds": r.get("bet365_close_favorite_odds") or "",
                "user_close_favorite_odds": r.get("user_close_favorite_odds") or "",
            }
            for r in qualified_closes[-5:]
        ],
    }

    payload = json.loads(BRIEF_JSON.read_text(encoding="utf-8"))
    payload["market_steam_watch"] = watch
    BRIEF_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = BRIEF_MD.read_text(encoding="utf-8").rstrip()
    block = [
        "",
        "---",
        "",
        "# MARKET STEAM WATCH — research only",
        "",
        "> This is **not R4 and not a bet signal**. It does not change the canonical R1/R2/R3 forward ledger.",
        "",
        f"- Scope: Premier League Favorite Steam M1 (+3 pp no-vig from frozen Bet365 opener).",
        f"- Frozen openers tracked: {len(openers)}",
        f"- Active +3 pp crossings: {len(active_crossings)}",
        f"- Observed closes: {len(closes)} | Close-qualified M1 watches: {len(qualified_closes)}",
        f"- Executable bookmaker being observed: {watch['user_bookmaker']}",
    ]
    if active_crossings:
        block += ["", "## Current crossings"]
        for r in active_crossings[-10:]:
            block.append(
                f"- WATCH | {r.get('home_team')} — {r.get('away_team')} | "
                f"opening favorite {r.get('opening_favorite')} | move {pct_text(r.get('movement_pp'))} | "
                f"Bet365 {r.get('bet365_cross_odds') or 'N/A'} | "
                f"{watch['user_bookmaker']} {r.get('user_cross_odds') or 'NO_PRICE'} | "
                f"{r.get('minutes_to_kickoff') or 'N/A'} min to kickoff"
            )
    else:
        block += ["", "- No active +3 pp crossing is currently recorded."]

    if qualified_closes:
        block += ["", "## Recent close-qualified watches"]
        for r in qualified_closes[-5:]:
            block.append(
                f"- {r.get('home_team')} — {r.get('away_team')} | move {pct_text(r.get('movement_pp'))} | "
                f"B365 close {r.get('bet365_close_favorite_odds') or 'N/A'} | "
                f"{watch['user_bookmaker']} close {r.get('user_close_favorite_odds') or 'NO_PRICE'}"
            )

    BRIEF_MD.write_text(md + "\n" + "\n".join(block) + "\n", encoding="utf-8")
    print(json.dumps({
        "stage61_watch_appended": True,
        "tracked_openers": len(openers),
        "active_crossings": len(active_crossings),
        "close_qualified": len(qualified_closes),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
