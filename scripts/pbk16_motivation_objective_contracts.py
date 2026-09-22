#!/usr/bin/env python3
"""PBK Item 13 — exact title/relegation objective-contract coverage.

This gate is deliberately descriptive. It converts already verified season
contracts into explicit PBK16 coverage and leaves every other league-season
UNKNOWN. It never infers relegation boundaries from table shape or provider
descriptions and grants no predictive/betting authority.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

try:
    from scripts import standings_format_registry as registry
except ModuleNotFoundError:
    import standings_format_registry as registry

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "ops" / "pbk16_domestic_league_format_inventory.csv"

TOP5_PROVIDER_TO_CODE = {
    "39": "E0",
    "140": "SP1",
    "135": "I1",
    "78": "D1",
    "61": "F1",
}


def season_label(season: Any) -> str:
    try:
        start=int(str(season).strip())
    except (TypeError,ValueError):
        return ""
    return f"{start}/{start+1}"


def read_inventory(path: Path = INVENTORY) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))


def cell_contract(row: dict[str, Any]) -> dict[str, Any]:
    league_id=str(row.get("provider_league_id") or "").strip()
    season=str(row.get("season") or "").strip()
    code=TOP5_PROVIDER_TO_CODE.get(league_id)

    if code:
        contract=registry.get_historical_top5_format(code,season_label(season))
        if contract.get("status")=="VERIFIED_RULE_CONTRACT":
            return {
                "status":"VERIFIED",
                "provider_league_id":league_id,
                "country":row.get("country"),
                "league_name":row.get("league_name"),
                "season":season,
                "source_contract":"HISTORICAL_TOP5_FORMATS",
                "title_boundary_authorized":True,
                "relegation_boundary_authorized":True,
                "total_games":contract.get("total_games"),
                "safe_rank":contract.get("safe_rank"),
                "direct_relegation_start_rank":contract.get(
                    "direct_relegation_start_rank"
                ),
                "relegation_playoff_rank":contract.get("relegation_playoff_rank"),
                "europe_status":"UNKNOWN_BY_DESIGN",
                "source":contract.get("source"),
            }

    return {
        "status":"UNKNOWN",
        "provider_league_id":league_id,
        "country":row.get("country"),
        "league_name":row.get("league_name"),
        "season":season,
        "source_contract":None,
        "title_boundary_authorized":False,
        "relegation_boundary_authorized":False,
        "total_games":None,
        "safe_rank":None,
        "direct_relegation_start_rank":None,
        "relegation_playoff_rank":None,
        "europe_status":"UNKNOWN_BY_DESIGN",
        "source":None,
    }


def build_coverage(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows=read_inventory() if rows is None else rows
    cells=[]
    seen=set()
    for row in rows:
        key=(
            str(row.get("provider_league_id") or "").strip(),
            str(row.get("season") or "").strip(),
        )
        if not all(key) or key in seen:
            continue
        seen.add(key)
        cells.append(cell_contract(row))

    verified=[row for row in cells if row["status"]=="VERIFIED"]
    missing=[row for row in cells if row["status"]!="VERIFIED"]
    leagues={row["provider_league_id"] for row in cells}

    return {
        "version":"PBK_ITEM13_EXACT_OBJECTIVE_CONTRACT_COVERAGE_V1",
        "status":"COMPLETE" if cells and not missing else "IN_PROGRESS",
        "required_league_season_cells":len(cells),
        "verified_league_season_cells":len(verified),
        "missing_league_season_cells":len(missing),
        "pbk16_leagues":len(leagues),
        "verified_countries":sorted({
            str(row.get("country") or "") for row in verified
            if str(row.get("country") or "")
        }),
        "missing_by_country":{
            country:sum(
                1 for row in missing if str(row.get("country") or "")==country
            )
            for country in sorted({
                str(row.get("country") or "") for row in missing
                if str(row.get("country") or "")
            })
        },
        "all_exact_title_relegation_contracts_verified":bool(cells and not missing),
        "historical_table_mutation_performed":False,
        "operational_betting_authority":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "missing_examples":missing[:20],
    }


if __name__=="__main__":
    import json
    print(json.dumps(build_coverage(),ensure_ascii=False,indent=2))
