#!/usr/bin/env python3
"""Item 13 — PBK16 historical non-regular phase contract registry.

This module does not mutate historical standings. It classifies every audited
non-regular TABLE_PHASE into explicit season-scoped contract buckets:

- CARRY_FORWARD_UNCHANGED_CANDIDATE: the historical format keeps accumulated
  league points across the phase boundary, but PBK still requires group-aware
  reconstruction before application.
- HALVE_FLOOR_WITH_ROUNDING_TIEBREAK: Austria's historical split applies the
  verified floor(points/2) transform and records the rounded-half tie-break;
- TRANSFORM_REQUIRED_NOT_IMPLEMENTED: a remaining season/competition-specific
  transform is not yet safe to apply.

The registry is season-scoped. No contract is inferred from a neighboring
season and no betting/model authority is granted.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

VERSION = "PBK_ITEM13_HISTORICAL_PHASE_CONTRACTS_V2"

CARRY = "CARRY_FORWARD_UNCHANGED_CANDIDATE"
HALVE = "HALVE_FLOOR_WITH_ROUNDING_TIEBREAK"
BELGIUM_HALF = "HALVE_CEIL_WITH_HALF_POINT_PENALTY"
TRANSFORM = "TRANSFORM_REQUIRED_NOT_IMPLEMENTED"

CONTRACTS: dict[tuple[str, str, str], dict[str, Any]] = {}


def _add(
    country, seasons, families, *, status, points_transform, source, reason,
    application_authorized=False, **metadata
):
    for season in seasons:
        for family in families:
            CONTRACTS[(country, str(season), family)] = {
                "status": status,
                "points_transform": points_transform,
                "application_authorized": bool(application_authorized),
                "group_aware_reconstruction_required": True,
                "source": source,
                "reason": reason,
                **metadata,
            }


# Denmark: split format introduced in 2016/17. PBK archive seasons 2017-2025
# retain accumulated league points into the table-bearing split phase.
_add(
    "Denmark",
    range(2017, 2026),
    ("CHAMPIONSHIP_SPLIT", "RELEGATION_SPLIT"),
    status=CARRY,
    points_transform="CARRY_FORWARD_UNCHANGED",
    application_authorized=True,
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
    application_authorized=True,
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
    application_authorized=True,
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
    application_authorized=True,
    source="https://www.wikizero.org/wiki/en/2019_A_Lyga",
    reason=(
        "A Lyga championship-round tables are cumulative from the regular "
        "phase; PBK does not yet authorize group-aware application."
    ),
)

# Austria: from 2018/19 through 2025/26 the table split after 22 rounds.
# Regular-season points were halved; half-points were rounded down. A club that
# lost a half-point in that rounding is ranked first when final-phase points tie.
_add(
    "Austria",
    range(2018, 2026),
    ("CHAMPIONSHIP_SPLIT", "RELEGATION_SPLIT"),
    status=HALVE,
    points_transform="FLOOR_HALF_AT_SPLIT",
    application_authorized=True,
    split_after_games=22,
    half_point_rounding="FLOOR",
    rounded_half_tiebreak="ROUNDED_DOWN_CLUB_FIRST",
    source=(
        "https://www.bundesliga.at/de/news/artikel/"
        "die-details-der-ligareform-so-wird-ab-2018-19-gespielt"
    ),
    reason=(
        "Official Austria Bundesliga reform contract: after 22 rounds points "
        "are halved, half-points are rounded down, and the rounded-half flag "
        "precedes the next final-phase tie-break criterion."
    ),
)

# Belgium: championship/europe play-offs halve regular-season points.
# Odd totals are rounded UP; the rounded half-point becomes a disadvantage at
# equal final-phase points. Relegation play-offs retain full points.
for season, families in {
    2017: ("CHAMPIONSHIP_SPLIT",),
    2018: ("CHAMPIONSHIP_SPLIT",),
    2020: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT"),
    2021: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT"),
    2022: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT"),
    2023: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT"),
    2024: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT"),
    2025: ("CHAMPIONSHIP_SPLIT", "EUROPE_SPLIT"),
}.items():
    _add(
        "Belgium",
        (season,),
        families,
        status=BELGIUM_HALF,
        points_transform="CEIL_HALF_AT_SPLIT",
        application_authorized=True,
        half_point_rounding="CEIL",
        rounded_half_tiebreak="ROUNDED_UP_CLUB_LAST",
        source="https://www.proleague.be/nieuws/hoe-verlopen-de-play-offs-in-het-seizoen-2024-25",
        reason=(
            "Official Pro League play-off contract: Champions/Europe play-off "
            "points are halved; odd totals are rounded up and the rounded-half "
            "club loses the first tie-break at equal final-phase points."
        ),
    )

_add(
    "Belgium",
    (2023, 2024, 2025),
    ("RELEGATION_SPLIT",),
    status=CARRY,
    points_transform="CARRY_FORWARD_UNCHANGED",
    application_authorized=True,
    source="https://www.proleague.be/nieuws/hoe-verlopen-de-play-offs-in-het-seizoen-2024-25",
    reason=(
        "Official Pro League Relegation Play-offs retain regular-season points "
        "without halving."
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
    halving = status_counts.get(HALVE, 0)
    belgium_halving = status_counts.get(BELGIUM_HALF, 0)
    transform = status_counts.get(TRANSFORM, 0)
    unknown_count = status_counts.get("UNKNOWN", 0)
    authorized = sum(
        1
        for row in required
        if lookup(row.get("country"), row.get("season"), row.get("phase_family"))
        .get("application_authorized")
    )

    return {
        "version": VERSION,
        "status": "OK" if required and unknown_count == 0 else "ATTENTION",
        "required_nonregular_table_phase_rows": len(required),
        "contract_covered_rows": len(required) - unknown_count,
        "carry_forward_candidate_rows": carry,
        "halving_authorized_rows": halving,
        "belgium_halving_authorized_rows": belgium_halving,
        "transform_required_rows": transform,
        "unknown_contract_rows": unknown_count,
        "country_required_rows": dict(sorted(country_counts.items())),
        "application_authorized_rows": authorized,
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
