#!/usr/bin/env python3
"""PBK Point14A — prematch availability and suspension resolution gate.

Purpose
-------
Resolve whether a player is eligible to enter Expected XI for one specific
fixture, using only evidence known before kickoff.

Important:
- a red card event alone does NOT automatically mean next-match suspension;
- competition scope must match the target fixture;
- confirmed suspension may later be appealed, reduced, overturned or served;
- an overturned suspension restores eligibility;
- appeal pending fails closed as UNCERTAIN, not automatic OUT;
- confirmed injury OUT remains unavailable;
- doubtful/questionable injury is uncertain, not automatic exclusion;
- no provider/network access;
- no probability/model/betting authority.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


FINAL_OUT_STATES = {
    "CONFIRMED_SUSPENSION",
    "CONFIRMED_INJURY_OUT",
    "TRANSFERRED_OUT",
    "NOT_REGISTERED",
}

UNCERTAIN_STATES = {
    "SUSPENSION_PENDING",
    "APPEAL_PENDING",
    "DOUBTFUL",
    "QUESTIONABLE",
    "UNKNOWN",
}

RESTORED_STATES = {
    "SUSPENSION_OVERTURNED",
    "SUSPENSION_SERVED",
    "APPEAL_UPHELD_NO_BAN",
    "AVAILABLE",
    "PRESENT",
}


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def _s(value: Any) -> str:
    return str(value or "").strip()


def _u(value: Any) -> str:
    return _s(value).upper()


def _competition_matches(event: dict[str, Any], target_competition: str) -> bool:
    scope = _u(event.get("competition_scope"))
    target = _u(target_competition)

    if not scope:
        return False

    if scope in {"ALL", "ALL_COMPETITIONS"}:
        return True

    return scope == target


def _event_is_known_before(
    event: dict[str, Any],
    before_utc: str,
) -> bool:
    observed = _dt(event.get("observed_at_utc"))
    cutoff = _dt(before_utc)
    return bool(observed and cutoff and observed <= cutoff)


def relevant_events(
    events: list[dict[str, Any]],
    *,
    player_id: str,
    team_id: str,
    target_competition: str,
    before_utc: str,
) -> list[dict[str, Any]]:
    """Return chronological explicit evidence relevant to target fixture."""
    out: list[tuple[datetime, dict[str, Any]]] = []

    for row in events or []:
        if _s(row.get("player_id")) != _s(player_id):
            continue
        if team_id and _s(row.get("team_id")) not in {"", _s(team_id)}:
            continue
        if not _event_is_known_before(row, before_utc):
            continue

        kind = _u(row.get("event_type"))

        if kind in {
            "INJURY",
            "TRANSFER",
            "REGISTRATION",
            "AVAILABILITY",
        }:
            observed = _dt(row.get("observed_at_utc"))
            out.append((observed, dict(row)))
            continue

        if kind in {"RED_CARD", "SUSPENSION", "APPEAL", "DISCIPLINE"}:
            if not _competition_matches(row, target_competition):
                continue
            observed = _dt(row.get("observed_at_utc"))
            out.append((observed, dict(row)))

    out.sort(key=lambda item: item[0])
    return [row for _, row in out]


def resolve_player_availability(
    events: list[dict[str, Any]],
    *,
    player_id: str,
    team_id: str,
    target_competition: str,
    before_utc: str,
) -> dict[str, Any]:
    """Resolve player eligibility for Expected XI."""

    rows = relevant_events(
        events,
        player_id=player_id,
        team_id=team_id,
        target_competition=target_competition,
        before_utc=before_utc,
    )

    current_status = "AVAILABLE"
    reason = "NO_BLOCKING_EVIDENCE"
    latest = None
    red_card_seen = False
    suspension_confirmed = False

    for row in rows:
        latest = row
        kind = _u(row.get("event_type"))
        status = _u(row.get("status"))

        if kind == "RED_CARD":
            red_card_seen = True
            current_status = "UNCERTAIN"
            reason = "RED_CARD_REQUIRES_SUSPENSION_VERIFICATION"
            continue

        if kind in {"SUSPENSION", "DISCIPLINE"}:
            if status == "CONFIRMED_SUSPENSION":
                suspension_confirmed = True
                current_status = "UNAVAILABLE"
                reason = "CONFIRMED_SUSPENSION"
            elif status in {"SUSPENSION_PENDING", "PENDING_REVIEW"}:
                current_status = "UNCERTAIN"
                reason = status
            elif status in {
                "SUSPENSION_OVERTURNED",
                "SUSPENSION_SERVED",
                "NO_SUSPENSION",
            }:
                suspension_confirmed = False
                current_status = "AVAILABLE"
                reason = status
            continue

        if kind == "APPEAL":
            if status == "APPEAL_PENDING":
                current_status = "UNCERTAIN"
                reason = "APPEAL_PENDING"
            elif status in {
                "SUSPENSION_OVERTURNED",
                "APPEAL_SUCCESSFUL",
                "APPEAL_UPHELD_NO_BAN",
            }:
                suspension_confirmed = False
                current_status = "AVAILABLE"
                reason = status
            elif status in {
                "APPEAL_REJECTED",
                "SUSPENSION_UPHELD",
            }:
                if suspension_confirmed:
                    current_status = "UNAVAILABLE"
                    reason = "SUSPENSION_UPHELD"
                else:
                    current_status = "UNCERTAIN"
                    reason = "APPEAL_REJECTED_WITHOUT_CONFIRMED_BAN"
            elif status == "SUSPENSION_REDUCED":
                current_status = "UNCERTAIN"
                reason = "SUSPENSION_REDUCED_REQUIRES_FIXTURE_SCOPE_RECHECK"
            continue

        if kind == "INJURY":
            if status in {"CONFIRMED_INJURY_OUT", "OUT"}:
                current_status = "UNAVAILABLE"
                reason = "CONFIRMED_INJURY_OUT"
            elif status in {"DOUBTFUL", "QUESTIONABLE"}:
                current_status = "UNCERTAIN"
                reason = status
            elif status in {"FIT", "CLEARED", "AVAILABLE"}:
                current_status = "AVAILABLE"
                reason = status
            continue

        if kind == "TRANSFER":
            if status == "TRANSFERRED_OUT":
                current_status = "UNAVAILABLE"
                reason = "TRANSFERRED_OUT"
            continue

        if kind == "REGISTRATION":
            if status == "NOT_REGISTERED":
                current_status = "UNAVAILABLE"
                reason = "NOT_REGISTERED"
            elif status == "REGISTERED":
                current_status = "AVAILABLE"
                reason = "REGISTERED"
            continue

        if kind == "AVAILABILITY":
            if status in RESTORED_STATES:
                current_status = "AVAILABLE"
                reason = status
            elif status in FINAL_OUT_STATES:
                current_status = "UNAVAILABLE"
                reason = status
            elif status in UNCERTAIN_STATES:
                current_status = "UNCERTAIN"
                reason = status

    hard_excluded = current_status == "UNAVAILABLE"

    return {
        "version": "PBK_POINT14_AVAILABILITY_GATE_V1",
        "player_id": _s(player_id),
        "team_id": _s(team_id),
        "target_competition": _s(target_competition),
        "before_utc": before_utc,
        "availability_status": current_status,
        "hard_excluded_from_expected_xi": hard_excluded,
        "start_probability_ceiling": 0.0 if hard_excluded else None,
        "resolution_reason": reason,
        "red_card_seen": red_card_seen,
        "confirmed_suspension_seen": suspension_confirmed,
        "relevant_event_count": len(rows),
        "latest_event_type": _u(latest.get("event_type")) if latest else None,
        "latest_event_status": _u(latest.get("status")) if latest else None,
        "latest_observed_at_utc": _s(latest.get("observed_at_utc")) if latest else None,
        "appeal_aware": True,
        "competition_aware": True,
        "no_lookahead": True,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }
