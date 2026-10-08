#!/usr/bin/env python3
"""PBK Match Passport Factor Registry V1.

Read-only registry describing which evidence/factor layers are connected to the
Match Passport and what authority each layer has.

The registry is deliberately non-scoring:
- no aggregate factor score;
- no probability mutation;
- no eligibility mutation;
- no stake mutation;
- double-counting groups are explicit;
- disconnected layers remain visible rather than silently omitted.
"""
from __future__ import annotations

REGISTRY_VERSION = "PBK_MATCH_PASSPORT_FACTOR_REGISTRY_V1"

EXPECTED_FACTORS = (
    "LINEUP_CONTEXT",
    "PLAYER_GRADE",
    "PLAYER_SYNERGY",
    "STYLE_MATCHUP",
    "MOTIVATION",
    "REFEREE",
    "CONGESTION",
    "INTERNATIONAL_LOAD",
    "ENVIRONMENT",
)

DOUBLE_COUNT_GROUPS = {
    "LINEUP_CONTEXT": "SQUAD_AVAILABILITY_XI",
    "PLAYER_GRADE": "PLAYER_QUALITY_FORM",
    "PLAYER_SYNERGY": "PLAYER_RELATIONSHIPS",
    "STYLE_MATCHUP": "TACTICAL_STYLE",
    "MOTIVATION": "MOTIVATION_OBJECTIVES",
    "REFEREE": "OFFICIATING",
    "CONGESTION": "SCHEDULE_LOAD",
    "INTERNATIONAL_LOAD": "SCHEDULE_LOAD",
    "ENVIRONMENT": "ENVIRONMENT_CONDITIONS",
}


def _connected_factor(
    factor_id,
    section,
    *,
    authority="RESEARCH_ONLY",
    evidence_time="PREMATCH_OR_FAIL_CLOSED",
    connected_section="",
):
    available = bool(isinstance(section, dict) and section.get("available"))
    status = "AVAILABLE" if available else "CONNECTED_NO_EVIDENCE"
    return {
        "factor_id": factor_id,
        "status": status,
        "available": available,
        "connected": True,
        "connected_section": connected_section,
        "evidence_time_contract": evidence_time,
        "authority": authority,
        "double_counting_group": DOUBLE_COUNT_GROUPS[factor_id],
        "read_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def _not_connected_factor(
    factor_id,
    *,
    authority="NOT_AUTHORIZED",
    evidence_time="PREMATCH_REQUIRED",
):
    return {
        "factor_id": factor_id,
        "status": "NOT_CONNECTED_TO_MATCH_PASSPORT",
        "available": False,
        "connected": False,
        "connected_section": "",
        "evidence_time_contract": evidence_time,
        "authority": authority,
        "double_counting_group": DOUBLE_COUNT_GROUPS[factor_id],
        "read_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def build_factor_registry(payload):
    payload = payload if isinstance(payload, dict) else {}

    factors = [
        _connected_factor(
            "LINEUP_CONTEXT",
            payload.get("lineup_context"),
            authority="CONTEXT_ONLY",
            connected_section="lineup_context",
        ),
        _connected_factor(
            "PLAYER_GRADE",
            payload.get("player_grade"),
            authority="RESEARCH_ONLY",
            connected_section="player_grade",
        ),
        _not_connected_factor("PLAYER_SYNERGY", authority="RESEARCH_ONLY"),
        _connected_factor(
            "STYLE_MATCHUP",
            payload.get("style_matchup"),
            authority="RESEARCH_ONLY",
            connected_section="style_matchup",
        ),
        _not_connected_factor("MOTIVATION", authority="FORWARD_REVIEW_ONLY"),
        _not_connected_factor("REFEREE", authority="CONTEXT_ONLY"),
        _not_connected_factor("CONGESTION", authority="CONTEXT_ONLY"),
        _not_connected_factor("INTERNATIONAL_LOAD", authority="CONTEXT_ONLY"),
        _not_connected_factor("ENVIRONMENT", authority="RESEARCH_ONLY"),
    ]

    connected = sum(1 for factor in factors if factor["connected"])
    available = sum(1 for factor in factors if factor["available"])

    return {
        "version": REGISTRY_VERSION,
        "factors": factors,
        "expected_factor_count": len(EXPECTED_FACTORS),
        "connected_factor_count": connected,
        "available_factor_count": available,
        "not_connected_factor_count": len(EXPECTED_FACTORS) - connected,
        "all_expected_factors_declared": tuple(
            factor["factor_id"] for factor in factors
        ) == EXPECTED_FACTORS,
        "aggregate_factor_score": None,
        "aggregate_score_authorized": False,
        "double_counting_guard": True,
        "read_only": True,
        "provider_polling": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "notes": (
            "Registry exposes factor wiring/authority only. "
            "It does not score, rank or mutate Match Passport decisions."
        ),
    }
