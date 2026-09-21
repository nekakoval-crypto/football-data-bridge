#!/usr/bin/env python3
"""Checklist item 13 — motivation foundation readiness.

Read-only, provider-free readiness over already materialized PBK motivation
layers. It never promotes a factor or grants probability/betting authority.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "ops"
CONFIG = ROOT / "config"

OUT = OPS / "motivation_foundation_readiness.json"
VERSION = "PBK_ITEM13_MOTIVATION_FOUNDATION_V1"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def build_readiness(ops: Path = OPS, config: Path = CONFIG) -> dict[str, Any]:
    top5 = read_json(ops / "stage80_top5_historical_motivation_last_run.json")
    market = read_json(ops / "stage80_top5_motivation_market_research_last_run.json")
    pbk16 = read_json(ops / "stage80_pbk16_historical_table_context_last_run.json")
    forward = read_json(ops / "standings_snapshot_last_run.json")
    rivalry = read_json(config / "pbk_motivation_rivalries_v1.json")

    top5_ok = (
        top5.get("status") == "OK"
        and int(top5.get("output_rows") or 0) == 16111
        and int(top5.get("league_season_cells") or 0) == 45
        and bool(top5.get("no_lookahead"))
        and not bool(top5.get("operational_betting_authority"))
    )
    market_ok = (
        market.get("status") == "OK"
        and int(market.get("joined_rows") or 0) == 16111
        and not bool(market.get("promotes_factor"))
        and not bool(market.get("operational_betting_authority"))
    )
    pbk16_table_ok = (
        pbk16.get("status") == "OK"
        and int(pbk16.get("source_domestic_rows") or 0) == 40989
        and int(pbk16.get("domestic_league_ids") or 0) == 16
        and bool(pbk16.get("no_lookahead"))
    )
    forward_capture_ok = (
        int(forward.get("tracked_leagues") or 0) == 16
        and bool(forward.get("provider_polling"))
    )
    rivalry_catalog_present = bool(rivalry.get("rivalries"))
    rivalry_catalog_complete = rivalry.get("status") == "VERIFIED_PBK16_CATALOG"

    exact_pbk16 = bool(pbk16.get("exact_title_relegation_motivation_allowed"))

    blockers = []
    if not top5_ok:
        blockers.append("TOP5_HISTORICAL_MOTIVATION_NOT_READY")
    if not market_ok:
        blockers.append("TOP5_MOTIVATION_MARKET_RESEARCH_NOT_READY")
    if not pbk16_table_ok:
        blockers.append("PBK16_HISTORICAL_TABLE_CONTEXT_NOT_READY")
    if not forward_capture_ok:
        blockers.append("PBK16_FORWARD_STANDINGS_CAPTURE_NOT_READY")
    if not exact_pbk16:
        blockers.append("PBK16_EXACT_TITLE_RELEGATION_MOTIVATION_NOT_AUTHORIZED")
    if not rivalry_catalog_present:
        blockers.append("RIVALRY_CATALOG_MISSING")
    elif not rivalry_catalog_complete:
        blockers.append("RIVALRY_CATALOG_PARTIAL")
    blockers.append("FORWARD_MOTIVATION_LABEL_AND_VALIDATION_RAIL_NOT_COMPLETE")
    blockers.append("MOTIVATION_SPECIALIST_PROBABILITY_MODEL_NOT_VALIDATED")

    data_ready = all(
        [top5_ok, market_ok, pbk16_table_ok, forward_capture_ok, rivalry_catalog_present]
    )
    foundation_complete = (
        data_ready
        and exact_pbk16
        and rivalry_catalog_complete
        and "FORWARD_MOTIVATION_LABEL_AND_VALIDATION_RAIL_NOT_COMPLETE" not in blockers
    )

    return {
        "version": VERSION,
        "status": "COMPLETE" if foundation_complete else "IN_PROGRESS",
        "checklist_item_13_data_engineering_foundation": (
            "COMPLETE" if foundation_complete else "IN_PROGRESS"
        ),
        "checklist_item_13_predictive_authority": "NOT_AUTHORIZED",
        "operational_betting_authority": False,
        "evidence": {
            "top5_historical_motivation_rows": int(top5.get("output_rows") or 0),
            "top5_historical_market_join_rows": int(market.get("joined_rows") or 0),
            "pbk16_historical_table_rows": int(pbk16.get("output_rows") or 0),
            "pbk16_historical_full_table_rows": int(
                pbk16.get("safe_regular_rows_with_full_table") or 0
            ),
            "pbk16_leagues": int(pbk16.get("domestic_league_ids") or 0),
            "forward_tracked_leagues": int(forward.get("tracked_leagues") or 0),
            "verified_rivalries": len(rivalry.get("rivalries") or []),
        },
        "capabilities": {
            "table_pressure_context": top5_ok and pbk16_table_ok,
            "historical_no_lookahead_research": top5_ok and market_ok,
            "forward_standings_snapshot_capture": forward_capture_ok,
            "derby_rivalry_context": rivalry_catalog_present,
            "direct_rival_context": True,
            "outcome_necessity_context": True,
            "generic_must_win_forbidden": True,
            "single_motivation_score_forbidden": True,
            "prematch_frozen_required": True,
        },
        "hard_blockers_to_foundation_closure": [
            item for item in blockers
            if item != "MOTIVATION_SPECIALIST_PROBABILITY_MODEL_NOT_VALIDATED"
        ],
        "hard_blockers_to_predictive_authority": blockers,
        "governance": {
            "no_lookahead": True,
            "unknown_not_zero": True,
            "no_fuzzy_rivalry_matching": True,
            "derby_independent_from_table_pressure": True,
            "no_probability_mutation": True,
            "no_eligibility_mutation": True,
            "no_stake_changes": True,
        },
    }


def main() -> int:
    payload = build_readiness()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
