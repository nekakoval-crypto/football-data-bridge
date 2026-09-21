#!/usr/bin/env python3
"""Item 13 — PBK16 historical non-regular phase contract registry.

This module does not mutate historical standings. It classifies every audited
non-regular TABLE_PHASE into one of two explicit buckets:

- CARRY_FORWARD_UNCHANGED_CANDIDATE: the historical format keeps accumulated
  league points across the phase boundary, but PBK still requires group-aware
  reconstruction before application.
- TRANSFORM_REQUIRED_NOT_IMPLEMENTED: the phase applies a season/competition
  specific points transform and remains fail-closed.

The registry is season-scoped. No contract is inferred from a neighboring
season and no betting/model authority is granted.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

VERSION = "PBK_ITEM13_HISTORICAL_PHASE_CONTRACTS_V1"

CARRY = "CARRY_FORWARD_UNCHANGED_CANDIDATE"
TRANSFORM = "TRANSFORM_REQUIRED_NOT_IMPLEMENTED"

CONTRACTS: dict[tuple[str, str, str], dict[str, Any]] = {}


def _add(country, seasons, families, *, status, points_transform, source, reason):
    for season in seasons:
        for family in families:
            CONTRACTS[(country, str(season), family)] = {
                "status": status,
                "points_transform": points_transform,
                "application_authorized": False,
                "group_aware_reconstruction_required": True,
                "source": source,
                "reason": reason,
            }


# Denmark: split format introduced in 2016/17. PBK archive seasons 2017-2025
# retain accumulated league points into the table-bearing split phase.
_add(
    "Denmark",
    range(2017, 2026),
    ("CHAMPIONSHIP_SPLIT", "RELEGATION_SPLIT"),
    status=CARRY,
    points_transform="CARRY_FORWARD_UNCHANGED",
    source="https://www.superliga.dk/struktur",
    reason=(
        "3F Superliga split structure is continuous league-table competition. "
        "PBK still requires group-aware ranking before using the split rows."
    ),
)

# Scotland: Premiership keeps a single season table, then separates top/bottom
# six after round 33 for the final five fixtures.
_add(
    "Scotland",
    (2017, 2018, 2020, 2021, 2022, 2023, 2024, 2025),
    ("CHAMPIONSHIP_OR_SPLIT", "RELEGATION_SPLIT"),
    status=CARRY,
    points_transform="CARRY_FORWARD_UNCHANGED",
    source="https://spfl.co.uk/league/premiership/table",
    reason=(
        "SPFL Premiership split preserves accumulated league points; PBK must "
        "reconstruct the two post-split groups before ranking is authoritative."
    ),
)

# Poland: archive has non-regular table phases only in 2018 and 2019 seasons.
# These ESA-37 seasons did not halve points between regular and final phases.
_add(
    "Poland",
    (2018, 2019),
    ("CHAMPIONSHIP_SPLIT", "RELEGATION_SPLIT"),
    status=CARRY,
    points_transform="CARRY_FORWARD_UNCHANGED",
    source="https://en.wikipedia.org/wiki/2017%E2%80%9318_Ekstraklasa",
    reason=(
        "ESA-37 final phase used carried regular-season points in this PBK "
        "window; group-aware ranking remains required."
    ),
)

# Lithuania: 2017-2019 archive contains a top-six championship phase; published
# season tables show cumulative points continuing into the championship round.
_add(
    "Lithuania",
    (2017, 2018, 2019),
    ("CHAMPIONSHIP_SPLIT",),
    status=CARRY,
    points_transform="CARRY_FORWARD_UNCHANGED",
    source="https://www.wikizero.org/wiki/en/2019_A_Lyga",
    reason=(
        "A Lyga championship-round tables are cumulative from the regular "
        "phase; PBK does not yet authorize group-aware application."
    ),
)

# Austria: historical seasons in this PBK window used point halving at the split.
# Exact transform/rounding is deliberately not implemented here.
_add(
    "Austria",
    range(2018, 2026),
    ("CHAMPIONSHIP_SPLIT", "RELEGATION_SPLIT"),
    status=TRANSFORM,
    points_transform="HISTORICAL_POINT_HALVING_RULE_REQUIRED",
    source=(
        "https://www.bundesliga.at/de/news/artikel/"
        "neu-ab-2026-27-keine-punkteteilung-neuer-tv-verteilungsschluessel-inkl-oesterreicher-topf"
    ),
    reason=(
        "Austria suspended point halving only from 2026/27, so historical "
        "split rows require the prior season-specific halving contract."
    ),
)

# Belgium changed split structures repeatedly across the PBK history window.
# Do not collapse championship/europe/relegation phases into one guessed rule.
for season, families in {
    2017: ("CHAMPIONSHIP_SPLIT",),
    2018: ("CHAMPIONSHIP_SPLIT",),
    2020: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT"),
    2021: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT"),
    2022: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT"),
    2023: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT", "RELEGATION_SPLIT"),
    2024: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT", "RELEGATION_SPLIT"),
    2025: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT", "RELEGATION_SPLIT"),
}.items():
    _add(
        "Belgium",
        (season,),
        families,
        status=TRANSFORM,
        points_transform="SEASON_AND_PHASE_SPECIFIC_RULE_REQUIRED",
        source="https://www.proleague.be/nieuws/vanaf-seizoen-26-27-met-18-clubs-in-de-jupiler-pro-league",
        reason=(
            "Belgian historical play-off structures changed across seasons; "
            "PBK requires explicit season+phase transforms before reconstruction."
        ),
    )


def lookup(country: Any, season: Any, phase_family: Any) -> dict[str, Any]:
    key = (
        str(country or "").strip(),
        str(season or "").strip(),
        str(phase_family or "").strip(),
    )
    item = CONTRACTS.get(key)
    if item:
        return {"country": key[0], "season": key[1], "phase_family": key[2], **item}
    return {
        "country": key[0],
        "season": key[1],
        "phase_family": key[2],
        "status": "UNKNOWN",
        "points_transform": None,
        "application_authorized": False,
        "group_aware_reconstruction_required": True,
        "source": None,
        "reason": "No exact season-scoped historical phase contract.",
    }


def analyze_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    required = [
        row for row in rows
        if str(row.get("phase_role") or "").strip() == "TABLE_PHASE"
        and str(row.get("season_format_contract_required") or "").strip().lower() == "true"
    ]
    status_counts = Counter()
    country_counts = Counter()
    unknown = []

    for row in required:
        contract = lookup(row.get("country"), row.get("season"), row.get("phase_family"))
        status_counts[contract["status"]] += 1
        country_counts[str(row.get("country") or "")] += 1
        if contract["status"] == "UNKNOWN":
            unknown.append({
                "country": row.get("country"),
                "season": row.get("season"),
                "phase_family": row.get("phase_family"),
                "fixture_id": row.get("fixture_id"),
            })

    carry = status_counts.get(CARRY, 0)
    transform = status_counts.get(TRANSFORM, 0)
    unknown_count = status_counts.get("UNKNOWN", 0)

    return {
        "version": VERSION,
        "status": "OK" if required and unknown_count == 0 else "ATTENTION",
        "required_nonregular_table_phase_rows": len(required),
        "contract_covered_rows": len(required) - unknown_count,
        "carry_forward_candidate_rows": carry,
        "transform_required_rows": transform,
        "unknown_contract_rows": unknown_count,
        "country_required_rows": dict(sorted(country_counts.items())),
        "application_authorized_rows": 0,
        "historical_table_mutation_performed": False,
        "exact_title_relegation_motivation_allowed": False,
        "operational_betting_authority": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "unknown_examples": unknown[:20],
    }


def analyze_csv(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return analyze_rows(list(csv.DictReader(stream)))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "ops" / "pbk16_domestic_phase_audit.csv"
    payload = analyze_csv(source)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
