#!/usr/bin/env python3
"""Validate the PBK hypothesis registry and its governance locks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "pbk_hypothesis_registry.json"
COMPETITION_SCOPE_PATH = ROOT / "config" / "pbk_competition_scope.json"

REQUIRED_FIELDS = {
    "id",
    "label",
    "family",
    "status",
    "authority",
    "market_scope",
    "competition_scope",
    "definition",
    "data_dependencies",
    "guardrails",
}

CANONICAL_LOCKS = {
    "R1": {
        "status": "CANONICAL",
        "authority": "CANONICAL",
        "competition_scope": ["Serie A"],
        "definition": "Serie A only; away team is unique minimum Bet365 1X2 favourite; 1.20 <= B365A < 2.10; P2; 1u.",
    },
    "R2": {
        "status": "CANONICAL",
        "authority": "CANONICAL",
        "competition_scope": ["Serie A"],
        "definition": "All R1 conditions; both teams have at least 5 previous current-season league matches; away last5 PPG > home last5 PPG; P2; 1u.",
    },
    "R3": {
        "status": "CANONICAL",
        "authority": "CANONICAL",
        "competition_scope": ["CORE_BIG5"],
        "definition": "Big-5 only; Monday in local league calendar; both teams have <=10 league matches remaining including current match; X; 1u.",
    },
}

REQUIRED_BRAIN_IDS = {
    "HIST_H2H_HOME_AWAY",
    "HIST_TEAM_HOME_AWAY_PROFILE",
    "HIST_WEEKDAY_TIME",
    "HIST_REST_SCHEDULE",
    "HIST_CUP_EUROPE_LOAD",
    "HIST_SEASON_STAGE_OBJECTIVE",
    "ODDS_BAND_FAVOURITE_UNDERDOG",
    "MARKET_TOTALS",
    "MARKET_BTTS",
    "MARKET_TEAM_TOTALS",
    "MARKET_HALF_HANDICAPS",
    "PLAYER_OVERALL_GRADE",
    "PLAYER_IMPORTANCE",
    "XI_QUALITY",
    "ROTATION_IMPACT",
    "ABSENCE_RETURN_IMPACT",
    "REFEREE_CONTEXT",
    "WEATHER_CONTEXT",
    "MARKET_MOVEMENT_CLV",
    "PROBABILITY_VALUE_ALL_MARKETS",
    "DECISION_ENGINE",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_registry(registry: dict, competition_scope: dict) -> list[str]:
    errors: list[str] = []

    statuses = set(registry.get("status_lifecycle", []))
    authorities = set(registry.get("authority_levels", []))
    hypotheses = registry.get("hypotheses", [])

    if registry.get("ui_freeze") is not True:
        errors.append("ui_freeze must remain true while the Brain checklist is under construction")
    if registry.get("auto_promotion") is not False:
        errors.append("auto_promotion must remain false")
    if competition_scope.get("scope_locked") is not True or competition_scope.get("total_leagues") != 16:
        errors.append("competition scope must remain locked to exactly 16 leagues")

    ids: list[str] = []
    by_id: dict[str, dict] = {}
    for row in hypotheses:
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            errors.append(f"{row.get('id', '<missing id>')}: missing required fields {sorted(missing)}")
            continue
        row_id = row["id"]
        ids.append(row_id)
        by_id[row_id] = row
        if row["status"] not in statuses:
            errors.append(f"{row_id}: invalid status {row['status']}")
        if row["authority"] not in authorities:
            errors.append(f"{row_id}: invalid authority {row['authority']}")
        if not row["market_scope"] or not row["competition_scope"]:
            errors.append(f"{row_id}: empty market/competition scope")
        if not isinstance(row["data_dependencies"], list) or not isinstance(row["guardrails"], list):
            errors.append(f"{row_id}: dependencies and guardrails must be lists")

    if len(ids) != len(set(ids)):
        errors.append("hypothesis ids must be unique")

    missing_brain = REQUIRED_BRAIN_IDS - set(ids)
    if missing_brain:
        errors.append(f"required Brain hypothesis families missing: {sorted(missing_brain)}")

    for strategy_id, lock in CANONICAL_LOCKS.items():
        row = by_id.get(strategy_id)
        if row is None:
            errors.append(f"missing canonical strategy {strategy_id}")
            continue
        if row.get("locked") is not True:
            errors.append(f"{strategy_id}: locked must be true")
        for field, expected in lock.items():
            if row.get(field) != expected:
                errors.append(f"{strategy_id}: locked {field} drifted; expected {expected!r}, got {row.get(field)!r}")

    h2h = by_id.get("HIST_H2H_HOME_AWAY", {})
    h2h_text = " ".join(h2h.get("guardrails", [])) + " " + h2h.get("definition", "")
    for required_phrase in ("sample size", "recency", "baseline"):
        if required_phrase.lower() not in h2h_text.lower():
            errors.append(f"HIST_H2H_HOME_AWAY must explicitly preserve {required_phrase}")

    decision = by_id.get("DECISION_ENGINE", {})
    decision_guards = " ".join(decision.get("guardrails", [])).lower()
    if "no automatic canonical promotion" not in decision_guards:
        errors.append("Decision Engine must forbid automatic canonical promotion")

    return errors


def main() -> int:
    registry = load_json(REGISTRY_PATH)
    competition_scope = load_json(COMPETITION_SCOPE_PATH)
    errors = validate_registry(registry, competition_scope)
    if errors:
        print("PBK hypothesis registry: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    hypotheses = registry["hypotheses"]
    print(
        "PBK hypothesis registry: OK | "
        f"hypotheses={len(hypotheses)} | "
        f"canonical={sum(row['authority'] == 'CANONICAL' for row in hypotheses)} | "
        f"research/watch/context={sum(row['authority'] != 'CANONICAL' for row in hypotheses)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
