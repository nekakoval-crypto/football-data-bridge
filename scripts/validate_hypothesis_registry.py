#!/usr/bin/env python3
"""Validate PBK Hypothesis Registry v2 and its governance locks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "pbk_hypothesis_registry.json"
COMPETITION_SCOPE_PATH = ROOT / "config" / "pbk_competition_scope.json"

EXPECTED_LIFECYCLE = [
    "IDEA", "SPEC_LOCKED", "HIST_TESTED", "PASSED", "FORWARD",
    "REVIEW", "CANONICAL", "REJECTED", "PAUSED",
]
EVIDENCE_KEYS = {"hist", "train", "test", "forward"}
REQUIRED_FIELDS = {
    "id", "label", "idea", "family", "status", "authority",
    "market_scope", "selection_scope", "competition_scope", "filters",
    "definition", "data_readiness", "data_dependencies",
    "evidence_stage", "guardrails",
}

CANONICAL_LOCKS = {
    "R1": {
        "status": "CANONICAL",
        "authority": "CANONICAL",
        "competition_scope": ["Serie A"],
        "selection_scope": ["P2"],
        "definition": "Serie A only; away team is unique minimum Bet365 1X2 favourite; 1.20 <= B365A < 2.10; P2; 1u.",
    },
    "R2": {
        "status": "CANONICAL",
        "authority": "CANONICAL",
        "competition_scope": ["Serie A"],
        "selection_scope": ["P2"],
        "definition": "All R1 conditions; both teams have at least 5 previous current-season league matches; away last5 PPG > home last5 PPG; P2; 1u.",
    },
    "R3": {
        "status": "CANONICAL",
        "authority": "CANONICAL",
        "competition_scope": ["CORE_BIG5"],
        "selection_scope": ["X"],
        "definition": "Big-5 only; Monday in local league calendar; both teams have <=10 league matches remaining including current match; X; 1u.",
    },
}

REQUIRED_BRAIN_IDS = {
    "GENERIC_1X2_PROBABILITY_V1",
    "HIST_H2H_HOME_AWAY",
    "HIST_TEAM_HOME_AWAY_PROFILE",
    "HIST_WEEKDAY_TIME",
    "HIST_REST_SCHEDULE",
    "HIST_CUP_EUROPE_LOAD",
    "HIST_SEASON_STAGE_OBJECTIVE",
    "ODDS_BAND_FAVOURITE_UNDERDOG",
    "MARKET_1X2_HOME_FAVOURITE",
    "MARKET_1X2_AWAY_FAVOURITE",
    "MARKET_1X2_DRAW",
    "MARKET_1X2_UNDERDOG",
    "MARKET_1X2_FADE_OVERVALUED_FAVOURITE",
    "MARKET_BIG_ODDS_LONGSHOT",
    "MARKET_TOTALS",
    "MARKET_BTTS",
    "MARKET_TEAM_TOTALS",
    "MARKET_HALF_HANDICAPS",
    "MARKET_DNB",
    "MARKET_DOUBLE_CHANCE",
    "MARKET_EUROPEAN_HANDICAP",
    "MARKET_ASIAN_HANDICAP",
    "PLAYER_OVERALL_GRADE",
    "PLAYER_FORM_GRADE",
    "PLAYER_IMPORTANCE",
    "XI_QUALITY",
    "ROTATION_IMPACT",
    "ABSENCE_RETURN_IMPACT",
    "ABSENCE_IMPACT",
    "RETURN_IMPACT",
    "TEAM_GRADES",
    "MATCHUP_GRADE",
    "REFEREE_CONTEXT",
    "WEATHER_CONTEXT",
    "MARKET_MOVEMENT_CLV",
    "HIGH_PROBABILITY_VS_VALUE",
    "LONGSHOT_UNDERDOG_ENGINE",
    "MARKET_SCANNER_ALL_SUPPORTED",
    "PROBABILITY_VALUE_ALL_MARKETS",
    "DECISION_ENGINE",
}

REQUIRED_SCANNER_SELECTIONS = {
    "P1", "X", "P2", "1X", "X2", "12", "F1", "F2", "DNB",
    "TB", "TM", "BTTS_YES", "BTTS_NO", "ITB1", "ITM1", "ITB2", "ITM2",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_registry(registry: dict, competition_scope: dict) -> list[str]:
    errors: list[str] = []

    lifecycle = registry.get("status_lifecycle", [])
    statuses = set(lifecycle)
    authorities = set(registry.get("authority_levels", []))
    readiness = set(registry.get("data_readiness_levels", []))
    hypotheses = registry.get("hypotheses", [])

    if registry.get("version") != 2:
        errors.append("registry version must be 2")
    if lifecycle != EXPECTED_LIFECYCLE:
        errors.append(f"status_lifecycle must equal {EXPECTED_LIFECYCLE!r}")
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
        if row["data_readiness"] not in readiness:
            errors.append(f"{row_id}: invalid data_readiness {row['data_readiness']}")
        if not row["market_scope"] or not row["selection_scope"] or not row["competition_scope"]:
            errors.append(f"{row_id}: empty market/selection/competition scope")
        if not isinstance(row["filters"], list):
            errors.append(f"{row_id}: filters must be a list")
        if not isinstance(row["data_dependencies"], list) or not isinstance(row["guardrails"], list):
            errors.append(f"{row_id}: dependencies and guardrails must be lists")
        stage = row.get("evidence_stage")
        if not isinstance(stage, dict) or set(stage) != EVIDENCE_KEYS:
            errors.append(f"{row_id}: evidence_stage must contain exactly {sorted(EVIDENCE_KEYS)}")
        elif any(not isinstance(stage[key], str) or not stage[key] for key in EVIDENCE_KEYS):
            errors.append(f"{row_id}: every evidence_stage value must be a non-empty string")

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
                errors.append(
                    f"{strategy_id}: locked {field} drifted; "
                    f"expected {expected!r}, got {row.get(field)!r}"
                )

    # DATA_READY is deliberately not a hypothesis status in v2. Availability is
    # represented only by data_readiness so "data exists" cannot mean "validated".
    if "DATA_READY" in statuses:
        errors.append("DATA_READY must not be a v2 hypothesis status")

    generic = by_id.get("GENERIC_1X2_PROBABILITY_V1", {})
    if generic:
        if generic.get("status") != "FORWARD" or generic.get("authority") != "RESEARCH":
            errors.append("Generic 1X2 v1 must remain FORWARD/RESEARCH until manual per-league review")
        if generic.get("validation_scope") != "PER_LEAGUE_FORWARD_ONLY":
            errors.append("Generic 1X2 v1 forward validation must be per league only")
        generic_evidence = generic.get("evidence_stage", {})
        if generic_evidence.get("test") != "PASSED_POOLED_BIG5_OOS_ONLY":
            errors.append("Generic 1X2 historical TEST evidence must remain pooled-Big5-only")
        if generic_evidence.get("forward") != "COLLECTING_PER_LEAGUE":
            errors.append("Generic 1X2 forward state must remain collecting per league")
        guards = " ".join(generic.get("guardrails", [])).lower()
        if "not league-specific" not in guards or "no historical backfill" not in guards:
            errors.append("Generic 1X2 must preserve pooled-only and no-backfill guardrails")

    h2h = by_id.get("HIST_H2H_HOME_AWAY", {})
    h2h_text = " ".join(h2h.get("guardrails", [])) + " " + h2h.get("definition", "")
    for required_phrase in ("sample size", "recency", "baseline"):
        if required_phrase.lower() not in h2h_text.lower():
            errors.append(f"HIST_H2H_HOME_AWAY must explicitly preserve {required_phrase}")

    combined = by_id.get("ABSENCE_RETURN_IMPACT", {})
    if combined.get("status") != "PAUSED" or set(combined.get("deprecated_by", [])) != {"ABSENCE_IMPACT", "RETURN_IMPACT"}:
        errors.append("legacy ABSENCE_RETURN_IMPACT must stay PAUSED and split into ABSENCE_IMPACT/RETURN_IMPACT")

    scanner = by_id.get("MARKET_SCANNER_ALL_SUPPORTED", {})
    if not REQUIRED_SCANNER_SELECTIONS.issubset(set(scanner.get("selection_scope", []))):
        errors.append("Market Scanner is missing required market selections")

    probability = by_id.get("PROBABILITY_VALUE_ALL_MARKETS", {})
    probability_guards = " ".join(probability.get("guardrails", [])).lower()
    if "never transfer probability" not in probability_guards:
        errors.append("Probability/value engine must forbid probability transfer across bets/markets")

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
    counts = {status: 0 for status in EXPECTED_LIFECYCLE}
    for row in hypotheses:
        counts[row["status"]] += 1
    print(
        "PBK hypothesis registry v2: OK | "
        f"hypotheses={len(hypotheses)} | "
        f"canonical={counts['CANONICAL']} | "
        f"forward={counts['FORWARD']} | "
        f"idea={counts['IDEA']} | "
        f"paused={counts['PAUSED']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
