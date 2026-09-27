from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def transfer_intent_decay(rounds_observed: int) -> float:
    """Research-only decay for transfer-intent prior as real-season evidence accumulates."""
    r = max(0, int(rounds_observed))
    if r <= 2:
        return 1.00
    if r <= 5:
        return 0.60
    if r <= 10:
        return 0.25
    return 0.05


def transfer_start_intent_prior(
    *,
    fee_club_percentile: float | None,
    fee_cohort_percentile: float | None,
    seasonal_spend_share: float | None,
    contract_years: float | None,
    positional_need: str | None,
    official_role_signal: str | None,
) -> dict[str, Any]:
    """
    Research-only intent feature. This is NOT P(start).

    Strongest evidence is explicit official role signal. Financial evidence is contextual,
    not absolute, and is combined conservatively to avoid a universal fee threshold.
    """
    official = (official_role_signal or "").upper().strip()
    need = (positional_need or "").upper().strip()

    if official in {"STARTER", "FIRST_TEAM_STARTER", "KEY_STARTER"}:
        level = "HIGH"
        reason = "OFFICIAL_ROLE_SIGNAL"
    else:
        parts = []
        for value in (fee_club_percentile, fee_cohort_percentile, seasonal_spend_share):
            if value is not None:
                parts.append(_clamp(float(value)))
        financial = sum(parts) / len(parts) if parts else None

        if financial is None and contract_years is None and not need:
            level = "UNKNOWN"
            reason = "INSUFFICIENT_EVIDENCE"
        else:
            score = 0.0
            weight = 0.0
            if financial is not None:
                score += financial * 0.65
                weight += 0.65
            if contract_years is not None:
                contract_component = _clamp((float(contract_years) - 2.0) / 4.0)
                score += contract_component * 0.15
                weight += 0.15
            if need:
                need_component = {
                    "VACANCY": 1.0,
                    "HIGH": 1.0,
                    "MEDIUM": 0.6,
                    "LOW": 0.2,
                    "CROWDED": 0.0,
                }.get(need, 0.4)
                score += need_component * 0.20
                weight += 0.20

            normalized = score / weight if weight else 0.0
            if normalized >= 0.72:
                level = "HIGH"
            elif normalized >= 0.42:
                level = "MEDIUM"
            else:
                level = "LOW"
            reason = "CONTEXTUAL_TRANSFER_INVESTMENT"

    return {
        "feature": "TRANSFER_START_INTENT_PRIOR",
        "level": level,
        "reason": reason,
        "probability_authority": "NOT_A_PROBABILITY",
        "research_only": True,
        "operational_betting_authority": False,
    }


def squad_hierarchy(
    *,
    starts: int,
    team_matches: int,
    minutes: int,
    available_matches: int | None = None,
) -> dict[str, Any]:
    """
    Current hierarchy from accumulated real matches.

    This is intentionally separate from match-specific Expected XI.
    """
    tm = max(0, int(team_matches))
    starts = max(0, int(starts))
    minutes = max(0, int(minutes))
    denom = max(1, int(available_matches if available_matches is not None else tm))

    start_share = starts / denom
    minute_share = minutes / max(1, denom * 90)

    if tm < 3:
        status = "HIERARCHY_EARLY_SAMPLE"
        tier = "UNKNOWN"
    elif start_share >= 0.70 or minute_share >= 0.72:
        status = "HIERARCHY_ESTABLISHED"
        tier = "CORE"
    elif start_share >= 0.35 or minute_share >= 0.40:
        status = "HIERARCHY_ESTABLISHED"
        tier = "ROTATION"
    elif starts > 0 or minutes > 0:
        status = "HIERARCHY_ESTABLISHED"
        tier = "DEPTH"
    else:
        status = "HIERARCHY_ESTABLISHED"
        tier = "DEVELOPMENT_OR_UNUSED"

    return {
        "feature": "SQUAD_HIERARCHY",
        "status": status,
        "tier": tier,
        "start_share": round(start_share, 4),
        "minute_share": round(minute_share, 4),
        "team_matches": tm,
        "research_only": True,
        "operational_betting_authority": False,
    }


def match_rotation_risk(
    *,
    rest_days: float | None,
    minutes_last_7d: int | None,
    matches_last_10d: int | None,
    matches_next_7d: int | None,
    historical_rotation_rate: float | None,
    next_match_importance_higher: bool | None,
) -> dict[str, Any]:
    """
    Match-specific rotation risk. It must NOT mutate the underlying squad hierarchy.
    """
    evidence = []
    points = 0

    if rest_days is not None and float(rest_days) <= 3.0:
        points += 2
        evidence.append("SHORT_REST")
    elif rest_days is not None and float(rest_days) <= 4.0:
        points += 1
        evidence.append("MODERATE_REST")

    if minutes_last_7d is not None and int(minutes_last_7d) >= 150:
        points += 2
        evidence.append("HIGH_7D_MINUTES")
    elif minutes_last_7d is not None and int(minutes_last_7d) >= 90:
        points += 1
        evidence.append("MEDIUM_7D_MINUTES")

    if matches_last_10d is not None and int(matches_last_10d) >= 3:
        points += 1
        evidence.append("RECENT_CONGESTION")

    if matches_next_7d is not None and int(matches_next_7d) >= 2:
        points += 1
        evidence.append("FORWARD_CONGESTION")

    if historical_rotation_rate is not None and float(historical_rotation_rate) >= 0.35:
        points += 1
        evidence.append("COACH_ROTATION_PATTERN")

    if next_match_importance_higher is True:
        points += 1
        evidence.append("NEXT_MATCH_PRIORITY")

    if points >= 5:
        level = "HIGH"
    elif points >= 2:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "feature": "MATCH_ROTATION_RISK",
        "level": level,
        "evidence": evidence,
        "research_only": True,
        "operational_betting_authority": False,
        "does_not_mutate_squad_hierarchy": True,
    }


def combine_hierarchy_and_transfer_prior(
    *,
    rounds_observed: int,
    hierarchy_tier: str,
    transfer_prior_level: str,
) -> dict[str, Any]:
    """
    Governs how much transfer prior is allowed to matter as rounds accumulate.
    """
    decay = transfer_intent_decay(rounds_observed)
    hierarchy = (hierarchy_tier or "UNKNOWN").upper()
    prior = (transfer_prior_level or "UNKNOWN").upper()

    if hierarchy != "UNKNOWN":
        authority = "REAL_MATCH_HIERARCHY_PRIMARY"
    elif prior in {"HIGH", "MEDIUM", "LOW"}:
        authority = "TRANSFER_PRIOR_TEMPORARY_TIEBREAKER"
    else:
        authority = "INSUFFICIENT_EVIDENCE"

    return {
        "rounds_observed": max(0, int(rounds_observed)),
        "transfer_prior_decay_weight": decay,
        "hierarchy_tier": hierarchy,
        "transfer_prior_level": prior,
        "authority": authority,
        "rules": {
            "transfer_fee_never_forces_start": True,
            "real_match_evidence_dominates_over_time": True,
            "rotation_does_not_erase_core_status": True,
            "expected_xi_is_match_specific": True,
        },
        "research_only": True,
        "operational_betting_authority": False,
    }
