from __future__ import annotations

from datetime import date
from typing import Any


PROVIDER_CANDIDATE_AUTHORITY = "PROVIDER_CAREER_CANDIDATE"


def _s(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _date(value: Any) -> date | None:
    text = _s(value)
    if not text:
        return None

    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _identity(row: dict[str, Any]) -> tuple[str, str]:
    return (
        _s(row.get("coach_id")),
        _s(row.get("coach_name")).casefold(),
    )


def _covers_date(
    row: dict[str, Any],
    as_of_date: date,
) -> bool:
    start = _date(
        row.get("start")
        or row.get("valid_from_utc")
    )
    end = _date(
        row.get("end")
        or row.get("valid_to_utc")
    )

    if not start:
        return False

    if as_of_date < start:
        return False

    if end and as_of_date >= end:
        return False

    return True


def assess_provider_career_ambiguity(
    rows: list[dict[str, Any]],
    *,
    team_id: str,
    as_of_date: str,
) -> dict[str, Any]:
    """
    Assess whether provider career history can identify one current
    coach candidate for a team.

    This contract is provider-evidence quality control only.
    It never grants historical authority and never promotes rows into
    HISTORICAL_VERIFIED.
    """

    target_date = _date(as_of_date)

    if not target_date:
        raise ValueError(
            f"Invalid as_of_date: {as_of_date!r}"
        )

    same_team = [
        dict(row)
        for row in rows
        if _s(row.get("team_id")) == _s(team_id)
    ]

    invalid_date_rows = [
        row
        for row in same_team
        if not _date(
            row.get("start")
            or row.get("valid_from_utc")
        )
    ]

    active_rows = [
        row
        for row in same_team
        if _covers_date(
            row,
            target_date,
        )
    ]

    distinct_active = {}

    for row in active_rows:
        identity = _identity(row)
        distinct_active.setdefault(
            identity,
            [],
        ).append(row)

    identities = list(
        distinct_active.keys()
    )

    base = {
        "version": (
            "PBK_COACH_PROVIDER_AMBIGUITY_V1"
        ),
        "team_id": _s(team_id),
        "as_of_date": target_date.isoformat(),
        "provider_row_count": len(same_team),
        "active_row_count": len(active_rows),
        "distinct_active_coach_count": (
            len(identities)
        ),
        "active_rows": active_rows,
        "invalid_date_row_count": (
            len(invalid_date_rows)
        ),
        "invalid_date_rows": invalid_date_rows,
        "candidate_authority": (
            PROVIDER_CANDIDATE_AUTHORITY
        ),
        "automatic_promotion": False,
        "historical_verified_created": False,
        "research_only": True,
        "operational_betting_authority": False,
    }

    if invalid_date_rows:
        return {
            **base,
            "status": (
                "PROVIDER_CAREER_DATE_INVALID"
            ),
            "selected_candidate": None,
        }

    if not active_rows:
        return {
            **base,
            "status": (
                "PROVIDER_CAREER_NO_ACTIVE_CANDIDATE"
            ),
            "selected_candidate": None,
        }

    if len(identities) > 1:
        return {
            **base,
            "status": (
                "PROVIDER_CAREER_AMBIGUOUS"
            ),
            "selected_candidate": None,
        }

    selected = active_rows[0]

    return {
        **base,
        "status": (
            "PROVIDER_CAREER_SINGLE_CANDIDATE"
        ),
        "selected_candidate": {
            "coach_id": _s(
                selected.get("coach_id")
            ),
            "coach_name": _s(
                selected.get("coach_name")
            ),
            "start": _s(
                selected.get("start")
                or selected.get(
                    "valid_from_utc"
                )
            ),
            "end": _s(
                selected.get("end")
                or selected.get(
                    "valid_to_utc"
                )
            ),
        },
    }
