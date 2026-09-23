#!/usr/bin/env python3
"""Fail-closed rivalry/derby context for PBK motivation.

The registry is intentionally explicit and exact-match only. Unknown pairs
remain UNKNOWN; no geography, fuzzy name matching, or result hindsight is used.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "pbk_motivation_rivalries_v1.json"


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": "PBK_MOTIVATION_RIVALRIES_V1",
            "status": "MISSING",
            "rivalries": [],
        }
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("rivalry registry must be an object")
    if not isinstance(payload.get("rivalries"), list):
        raise ValueError("rivalries must be a list")
    return payload


def _alias_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {_norm(value) for value in values if _norm(value)}



PBK16_RIVALRY_SCOPES = {
    "ENGLAND",
    "SPAIN",
    "ITALY",
    "GERMANY",
    "FRANCE",
    "AUSTRIA",
    "BELGIUM",
    "DENMARK",
    "LITHUANIA",
    "LATVIA",
    "NETHERLANDS",
    "NORWAY",
    "POLAND",
    "PORTUGAL",
    "TURKEY",
    "SCOTLAND",
}

ALLOWED_RIVALRY_CLASSES = {
    "LOCAL_DERBY",
    "CITY_DERBY",
    "REGIONAL_DERBY",
    "NATIONAL_RIVALRY",
    "HISTORIC_RIVALRY",
}

REQUIRED_RIVALRY_FIELDS = {
    "id",
    "rivalry_name",
    "rivalry_type",
    "competition_scope",
    "principled_rivalry",
    "team_a_aliases",
    "team_b_aliases",
    "rivalry_classes",
    "derby_label",
    "valid_from_season",
    "valid_to_season",
}


def registry_readiness(
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = (
        registry
        if registry is not None
        else load_registry()
    )

    rivalries = payload.get("rivalries")
    if not isinstance(rivalries, list):
        rivalries = []

    blockers = []

    matching_policy = str(
        payload.get("matching_policy") or ""
    )

    if (
        matching_policy
        != "EXACT_NORMALIZED_ALIAS_ONLY_NO_FUZZY"
    ):
        blockers.append("MATCHING_POLICY_NOT_EXACT_ONLY")

    ids = []
    scopes = set()
    pair_owners = {}
    malformed = []
    invalid_classes = []
    empty_aliases = []

    for index, row in enumerate(rivalries):
        if not isinstance(row, dict):
            malformed.append(f"ROW_{index}")
            continue

        rid = str(row.get("id") or "").strip()
        ids.append(rid)

        missing = sorted(
            field
            for field in REQUIRED_RIVALRY_FIELDS
            if field not in row
        )

        if missing:
            malformed.append(
                f"{rid or 'ROW_' + str(index)}:"
                + ",".join(missing)
            )

        scope = str(
            row.get("competition_scope") or ""
        ).upper().strip()

        if scope:
            scopes.add(scope)

        a = _alias_set(row.get("team_a_aliases"))
        b = _alias_set(row.get("team_b_aliases"))

        if not a or not b:
            empty_aliases.append(
                rid or f"ROW_{index}"
            )

        classes = {
            str(value or "").upper().strip()
            for value in (
                row.get("rivalry_classes") or []
            )
            if str(value or "").strip()
        }

        if (
            not classes
            or not classes.issubset(
                ALLOWED_RIVALRY_CLASSES
            )
        ):
            invalid_classes.append(
                rid or f"ROW_{index}"
            )

        # Detect exact pair collisions that would make lookup
        # AMBIGUOUS. This is conservative: even if two contracts
        # are time-bounded, duplicate exact pairs are not allowed
        # in the V2 baseline until temporal overlap resolution is
        # modeled explicitly.
        for left in a:
            for right in b:
                pair = (
                    scope,
                    tuple(sorted((left, right))),
                )
                pair_owners.setdefault(
                    pair,
                    set(),
                ).add(rid)

    duplicate_ids = sorted(
        value
        for value in set(ids)
        if value and ids.count(value) > 1
    )

    ambiguous_pairs = sorted(
        {
            "|".join(
                [pair[0], *pair[1]]
            )
            for pair, owners
            in pair_owners.items()
            if len(owners) > 1
        }
    )

    missing_scopes = sorted(
        PBK16_RIVALRY_SCOPES - scopes
    )

    unexpected_scopes = sorted(
        scopes - PBK16_RIVALRY_SCOPES
    )

    if not rivalries:
        blockers.append("RIVALRY_CATALOG_EMPTY")

    if missing_scopes:
        blockers.append(
            "PBK16_SCOPES_MISSING"
        )

    if unexpected_scopes:
        blockers.append(
            "UNEXPECTED_COMPETITION_SCOPES"
        )

    if duplicate_ids:
        blockers.append("DUPLICATE_RIVALRY_IDS")

    if ambiguous_pairs:
        blockers.append(
            "AMBIGUOUS_EXACT_ALIAS_PAIRS"
        )

    if malformed:
        blockers.append(
            "MALFORMED_RIVALRY_CONTRACTS"
        )

    if empty_aliases:
        blockers.append(
            "EMPTY_RIVALRY_ALIASES"
        )

    if invalid_classes:
        blockers.append(
            "INVALID_RIVALRY_CLASSES"
        )

    coverage = payload.get("coverage") or {}

    if (
        coverage.get("exhaustiveness")
        != "NON_EXHAUSTIVE_BY_DESIGN"
    ):
        blockers.append(
            "EXHAUSTIVENESS_POLICY_NOT_EXPLICIT"
        )

    if (
        coverage.get("unknown_pair_policy")
        != "UNKNOWN"
    ):
        blockers.append(
            "UNKNOWN_PAIR_POLICY_NOT_FAIL_CLOSED"
        )

    verified = (
        not blockers
        and payload.get("status")
        == "VERIFIED_PBK16_CATALOG"
        and scopes == PBK16_RIVALRY_SCOPES
    )

    return {
        "status": (
            "VERIFIED_PBK16_CATALOG"
            if verified
            else "PARTIAL_VERIFIED_CATALOG"
        ),
        "verified": verified,
        "catalog_status_declared": str(
            payload.get("status") or "UNKNOWN"
        ),
        "catalog_version": str(
            payload.get("version") or "UNKNOWN"
        ),
        "matching_policy": matching_policy,
        "verified_contracts": len(rivalries),
        "pbk16_leagues_represented": len(
            scopes & PBK16_RIVALRY_SCOPES
        ),
        "required_pbk16_leagues": len(
            PBK16_RIVALRY_SCOPES
        ),
        "scopes": sorted(scopes),
        "missing_scopes": missing_scopes,
        "unexpected_scopes": unexpected_scopes,
        "duplicate_ids": duplicate_ids,
        "ambiguous_exact_pairs": ambiguous_pairs,
        "malformed_contracts": malformed,
        "empty_alias_contracts": empty_aliases,
        "invalid_class_contracts": invalid_classes,
        "exhaustiveness": coverage.get(
            "exhaustiveness"
        ),
        "unknown_pair_policy": coverage.get(
            "unknown_pair_policy"
        ),
        "blockers": blockers,
        "operational_betting_authority": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }



def lookup_rivalry(
    home_team: Any,
    away_team: Any,
    *,
    season: Any = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = registry if registry is not None else load_registry()
    home = _norm(home_team)
    away = _norm(away_team)

    result = {
        "status": "UNKNOWN",
        "registry_status": str(payload.get("status") or "UNKNOWN"),
        "registry_version": str(payload.get("version") or "UNKNOWN"),
        "rivalry_id": None,
        "rivalry_name": None,
        "rivalry_type": None,
        "rivalry_classes": [],
        "derby": False,
        "derby_label": False,
        "principled_rivalry": False,
        "valid_from_season": None,
        "valid_to_season": None,
        "independent_of_table_pressure": True,
        "matching_policy": str(
            payload.get("matching_policy")
            or "EXACT_NORMALIZED_ALIAS_ONLY_NO_FUZZY"
        ),
    }

    if not home or not away:
        return result

    def _season_start(value: Any) -> int | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return int(raw[:4])
        except (TypeError, ValueError):
            return None

    requested_season = _season_start(season)

    matches = []
    for row in payload.get("rivalries") or []:
        if not isinstance(row, dict):
            continue

        a = _alias_set(row.get("team_a_aliases"))
        b = _alias_set(row.get("team_b_aliases"))

        pair_match = (
            (home in a and away in b)
            or (home in b and away in a)
        )
        if not pair_match:
            continue

        valid_from = _season_start(row.get("valid_from_season"))
        valid_to = _season_start(row.get("valid_to_season"))

        # Fail closed for time-bounded rivalry contracts when the fixture
        # season is unknown.
        if (valid_from is not None or valid_to is not None) and requested_season is None:
            continue

        if valid_from is not None and requested_season < valid_from:
            continue

        if valid_to is not None and requested_season > valid_to:
            continue

        matches.append(row)

    if len(matches) != 1:
        if len(matches) > 1:
            result["status"] = "AMBIGUOUS"
        return result

    row = matches[0]
    rivalry_type = str(row.get("rivalry_type") or "").upper() or None

    rivalry_classes = [
        str(value).upper()
        for value in (row.get("rivalry_classes") or [])
        if str(value or "").strip()
    ]

    derby_label = (
        bool(row.get("derby_label"))
        if "derby_label" in row
        else rivalry_type == "DERBY"
    )

    result.update(
        status="VERIFIED",
        rivalry_id=row.get("id"),
        rivalry_name=row.get("rivalry_name"),
        rivalry_type=rivalry_type,
        rivalry_classes=rivalry_classes,
        derby=derby_label,
        derby_label=derby_label,
        principled_rivalry=bool(row.get("principled_rivalry")),
        valid_from_season=row.get("valid_from_season"),
        valid_to_season=row.get("valid_to_season"),
    )
    return result


def fixture_rivalry(
    fixture: dict[str, Any],
    *,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return lookup_rivalry(
        fixture.get("home_team"),
        fixture.get("away_team"),
        season=fixture.get("season"),
        registry=registry,
    )
