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
