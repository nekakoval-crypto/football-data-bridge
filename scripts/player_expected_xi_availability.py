#!/usr/bin/env python3
"""PBK Point14A — prematch availability resolution gate V2.

Availability dimensions are independent.

A medical event cannot clear a disciplinary suspension.
A successful disciplinary appeal cannot clear a medical OUT.
Transfer/registration blockers are also independent.

Final state:
- UNAVAILABLE if ANY domain is unavailable;
- UNCERTAIN if no domain is unavailable but ANY domain is uncertain;
- AVAILABLE only when no blocking/uncertain domain remains.

Red card alone never proves next-match suspension.
Suspension scope is competition-aware.
Appeals may overturn, uphold or reduce a suspension.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def _s(value: Any) -> str:
    return str(value or "").strip()


def _u(value: Any) -> str:
    return _s(value).upper()


def _competition_matches(
    event: dict[str, Any],
    target_competition: str,
) -> bool:
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

    return bool(
        observed
        and cutoff
        and observed <= cutoff
    )


def relevant_events(
    events: list[dict[str, Any]],
    *,
    player_id: str,
    team_id: str,
    target_competition: str,
    before_utc: str,
) -> list[dict[str, Any]]:

    out: list[tuple[datetime, dict[str, Any]]] = []

    for row in events or []:

        if _s(row.get("player_id")) != _s(player_id):
            continue

        if team_id and _s(row.get("team_id")) not in {
            "",
            _s(team_id),
        }:
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

        if kind in {
            "RED_CARD",
            "SUSPENSION",
            "APPEAL",
            "DISCIPLINE",
        }:
            if not _competition_matches(
                row,
                target_competition,
            ):
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

    rows = relevant_events(
        events,
        player_id=player_id,
        team_id=team_id,
        target_competition=target_competition,
        before_utc=before_utc,
    )

    domains = {
        "DISCIPLINE": {
            "status": "AVAILABLE",
            "reason": "",
        },
        "MEDICAL": {
            "status": "AVAILABLE",
            "reason": "",
        },
        "TRANSFER": {
            "status": "AVAILABLE",
            "reason": "",
        },
        "REGISTRATION": {
            "status": "AVAILABLE",
            "reason": "",
        },
        "GENERAL": {
            "status": "AVAILABLE",
            "reason": "",
        },
    }

    latest = None
    red_card_seen = False
    suspension_confirmed = False

    for row in rows:

        latest = row

        kind = _u(row.get("event_type"))
        status = _u(row.get("status"))

        # -----------------------------------------------------
        # DISCIPLINE
        # -----------------------------------------------------

        if kind == "RED_CARD":

            red_card_seen = True

            domains["DISCIPLINE"] = {
                "status": "UNCERTAIN",
                "reason": (
                    "RED_CARD_REQUIRES_"
                    "SUSPENSION_VERIFICATION"
                ),
            }

            continue

        if kind in {"SUSPENSION", "DISCIPLINE"}:

            if status == "CONFIRMED_SUSPENSION":

                suspension_confirmed = True

                domains["DISCIPLINE"] = {
                    "status": "UNAVAILABLE",
                    "reason": "CONFIRMED_SUSPENSION",
                }

            elif status in {
                "SUSPENSION_PENDING",
                "PENDING_REVIEW",
            }:

                domains["DISCIPLINE"] = {
                    "status": "UNCERTAIN",
                    "reason": status,
                }

            elif status in {
                "SUSPENSION_OVERTURNED",
                "SUSPENSION_SERVED",
                "NO_SUSPENSION",
            }:

                suspension_confirmed = False

                domains["DISCIPLINE"] = {
                    "status": "AVAILABLE",
                    "reason": status,
                }

            continue

        if kind == "APPEAL":

            if status == "APPEAL_PENDING":

                domains["DISCIPLINE"] = {
                    "status": "UNCERTAIN",
                    "reason": "APPEAL_PENDING",
                }

            elif status in {
                "SUSPENSION_OVERTURNED",
                "APPEAL_SUCCESSFUL",
                "APPEAL_UPHELD_NO_BAN",
            }:

                suspension_confirmed = False

                domains["DISCIPLINE"] = {
                    "status": "AVAILABLE",
                    "reason": status,
                }

            elif status in {
                "APPEAL_REJECTED",
                "SUSPENSION_UPHELD",
            }:

                if suspension_confirmed:

                    domains["DISCIPLINE"] = {
                        "status": "UNAVAILABLE",
                        "reason": "SUSPENSION_UPHELD",
                    }

                else:

                    domains["DISCIPLINE"] = {
                        "status": "UNCERTAIN",
                        "reason": (
                            "APPEAL_REJECTED_WITHOUT_"
                            "CONFIRMED_BAN"
                        ),
                    }

            elif status == "SUSPENSION_REDUCED":

                domains["DISCIPLINE"] = {
                    "status": "UNCERTAIN",
                    "reason": (
                        "SUSPENSION_REDUCED_REQUIRES_"
                        "FIXTURE_SCOPE_RECHECK"
                    ),
                }

            continue

        # -----------------------------------------------------
        # MEDICAL
        # -----------------------------------------------------

        if kind == "INJURY":

            if status in {
                "CONFIRMED_INJURY_OUT",
                "OUT",
            }:

                domains["MEDICAL"] = {
                    "status": "UNAVAILABLE",
                    "reason": "CONFIRMED_INJURY_OUT",
                }

            elif status in {
                "DOUBTFUL",
                "QUESTIONABLE",
            }:

                domains["MEDICAL"] = {
                    "status": "UNCERTAIN",
                    "reason": status,
                }

            elif status in {
                "FIT",
                "CLEARED",
                "AVAILABLE",
            }:

                domains["MEDICAL"] = {
                    "status": "AVAILABLE",
                    "reason": status,
                }

            continue

        # -----------------------------------------------------
        # TRANSFER
        # -----------------------------------------------------

        if kind == "TRANSFER":

            if status == "TRANSFERRED_OUT":

                domains["TRANSFER"] = {
                    "status": "UNAVAILABLE",
                    "reason": "TRANSFERRED_OUT",
                }

            elif status in {
                "TRANSFERRED_IN",
                "ACTIVE_AT_CLUB",
            }:

                domains["TRANSFER"] = {
                    "status": "AVAILABLE",
                    "reason": status,
                }

            continue

        # -----------------------------------------------------
        # REGISTRATION
        # -----------------------------------------------------

        if kind == "REGISTRATION":

            if status == "NOT_REGISTERED":

                domains["REGISTRATION"] = {
                    "status": "UNAVAILABLE",
                    "reason": "NOT_REGISTERED",
                }

            elif status == "REGISTERED":

                domains["REGISTRATION"] = {
                    "status": "AVAILABLE",
                    "reason": "REGISTERED",
                }

            continue

        # -----------------------------------------------------
        # GENERAL
        # -----------------------------------------------------

        if kind == "AVAILABILITY":

            if status in {
                "AVAILABLE",
                "PRESENT",
            }:

                domains["GENERAL"] = {
                    "status": "AVAILABLE",
                    "reason": status,
                }

            elif status in {
                "ABSENT",
                "UNAVAILABLE",
            }:

                domains["GENERAL"] = {
                    "status": "UNAVAILABLE",
                    "reason": status,
                }

            elif status in {
                "UNKNOWN",
                "DOUBTFUL",
                "QUESTIONABLE",
            }:

                domains["GENERAL"] = {
                    "status": "UNCERTAIN",
                    "reason": status,
                }

    blocking_reasons = [
        value["reason"]
        for value in domains.values()
        if value["status"] == "UNAVAILABLE"
        and value["reason"]
    ]

    uncertainty_reasons = [
        value["reason"]
        for value in domains.values()
        if value["status"] == "UNCERTAIN"
        and value["reason"]
    ]

    if blocking_reasons:

        final_status = "UNAVAILABLE"
        resolution_reason = blocking_reasons[0]

    elif uncertainty_reasons:

        final_status = "UNCERTAIN"
        resolution_reason = uncertainty_reasons[0]

    else:

        final_status = "AVAILABLE"
        restored = [
            value["reason"]
            for value in domains.values()
            if value["status"] == "AVAILABLE"
            and value["reason"]
        ]

        resolution_reason = (
            restored[-1]
            if restored
            else "NO_BLOCKING_EVIDENCE"
        )

    return {
        "version": "PBK_POINT14_AVAILABILITY_GATE_V2",
        "player_id": _s(player_id),
        "team_id": _s(team_id),
        "target_competition": _s(target_competition),
        "before_utc": before_utc,

        "availability_status": final_status,

        "hard_excluded_from_expected_xi": (
            final_status == "UNAVAILABLE"
        ),

        "start_probability_ceiling": (
            0.0
            if final_status == "UNAVAILABLE"
            else None
        ),

        "resolution_reason": resolution_reason,

        "blocking_reasons": blocking_reasons,
        "uncertainty_reasons": uncertainty_reasons,

        "domain_states": domains,

        "red_card_seen": red_card_seen,

        "confirmed_suspension_seen": (
            suspension_confirmed
        ),

        "relevant_event_count": len(rows),

        "latest_event_type": (
            _u(latest.get("event_type"))
            if latest else None
        ),

        "latest_event_status": (
            _u(latest.get("status"))
            if latest else None
        ),

        "latest_observed_at_utc": (
            _s(latest.get("observed_at_utc"))
            if latest else None
        ),

        "independent_domains": True,
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
