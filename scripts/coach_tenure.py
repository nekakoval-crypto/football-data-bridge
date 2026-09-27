from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


OPS = Path("ops")

COACH_TENURE_HISTORY = (
    OPS / "coach_tenure_history.csv"
)

FIELDS = [
    "team_id",
    "team_name",
    "coach_id",
    "coach_name",
    "valid_from_utc",
    "valid_to_utc",
    "effective_precision",
    "source_type",
    "source_ref",
    "observed_at_utc",
    "temporal_authority",
    "evidence_quality",
    "notes",
]


AUTHORIZED_TEMPORAL_AUTHORITIES = {
    "HISTORICAL_VERIFIED",
    "PREMATCH_FROZEN",
}


NON_AUTHORITATIVE_TEMPORAL_AUTHORITIES = {
    "PROVIDER_CAREER_CANDIDATE",
    "RETROSPECTIVE_ONLY",
    "DISCOVERY_CLUE",
    "RESEARCH_CANDIDATE",
}


VALID_EFFECTIVE_PRECISIONS = {
    "DATE",
    "DATETIME",
}


def _s(value: Any) -> str:
    return str(
        value
        if value is not None
        else ""
    ).strip()


def _u(value: Any) -> str:
    return _s(value).upper()


def _dt(
    value: Any,
) -> datetime | None:

    text = _s(value)

    if not text:
        return None

    try:
        result = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if result.tzinfo is None:
        return None

    return result.astimezone(
        timezone.utc
    )


def _date(
    value: Any,
) -> date | None:

    text = _s(value)

    if not text:
        return None

    try:
        return date.fromisoformat(
            text[:10]
        )
    except ValueError:
        return None


def effective_precision(
    row: dict[str, Any],
) -> str:

    explicit = _u(
        row.get("effective_precision")
    )

    if explicit in VALID_EFFECTIVE_PRECISIONS:
        return explicit

    start = _s(
        row.get("valid_from_utc")
    )

    end = _s(
        row.get("valid_to_utc")
    )

    values = [
        value
        for value in (start, end)
        if value
    ]

    if values and all(
        "T" not in value
        for value in values
    ):
        return "DATE"

    return "DATETIME"


def read_coach_tenures(
    path: Path = COACH_TENURE_HISTORY,
) -> list[dict[str, str]]:

    if not path.exists():
        return []

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        return list(
            csv.DictReader(stream)
        )


def row_is_authoritative(
    row: dict[str, Any],
) -> bool:

    return (
        _u(
            row.get(
                "temporal_authority"
            )
        )
        in AUTHORIZED_TEMPORAL_AUTHORITIES
    )


def row_is_provider_candidate(
    row: dict[str, Any],
) -> bool:

    return (
        _u(
            row.get(
                "temporal_authority"
            )
        )
        == "PROVIDER_CAREER_CANDIDATE"
    )


def coverage_state(
    row: dict[str, Any],
    as_of_utc: str,
) -> str:

    precision = effective_precision(
        row
    )

    if precision == "DATETIME":

        target = _dt(as_of_utc)
        start = _dt(
            row.get("valid_from_utc")
        )
        end = _dt(
            row.get("valid_to_utc")
        )

        if not target or not start:
            return "INVALID"

        if target < start:
            return "NOT_COVERED"

        if end and target >= end:
            return "NOT_COVERED"

        return "COVERED"


    target_dt = _dt(as_of_utc)

    if not target_dt:
        return "INVALID"

    target_date = target_dt.date()

    start_date = _date(
        row.get("valid_from_utc")
    )

    end_date = _date(
        row.get("valid_to_utc")
    )

    if not start_date:
        return "INVALID"

    if target_date < start_date:
        return "NOT_COVERED"

    if target_date == start_date:
        return (
            "DATE_BOUNDARY_UNCERTAIN"
        )

    if end_date:

        if target_date > end_date:
            return "NOT_COVERED"

        if target_date == end_date:
            return (
                "DATE_BOUNDARY_UNCERTAIN"
            )

    return "COVERED"


def row_covers_time(
    row: dict[str, Any],
    as_of_utc: str,
) -> bool:

    return (
        coverage_state(
            row,
            as_of_utc,
        )
        == "COVERED"
    )


def compare_candidate_to_verified(
    candidate: dict[str, Any],
    verified_rows: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    if not row_is_provider_candidate(
        candidate
    ):
        return {
            "version": (
                "PBK_COACH_SOURCE_AUTHORITY_V1"
            ),
            "status": (
                "NOT_PROVIDER_CANDIDATE"
            ),
            "automatic_promotion": False,
        }

    same_team = [
        row
        for row in verified_rows
        if (
            _s(row.get("team_id"))
            == _s(
                candidate.get("team_id")
            )
        )
        and row_is_authoritative(row)
    ]

    if not same_team:
        return {
            "version": (
                "PBK_COACH_SOURCE_AUTHORITY_V1"
            ),
            "status": (
                "NO_VERIFIED_COMPARATOR"
            ),
            "automatic_promotion": False,
            "candidate_authority": (
                "PROVIDER_CAREER_CANDIDATE"
            ),
        }

    candidate_coach_id = _s(
        candidate.get("coach_id")
    )

    candidate_name = _s(
        candidate.get("coach_name")
    ).casefold()

    coach_matches = []

    for row in same_team:

        verified_id = _s(
            row.get("coach_id")
        )

        verified_name = _s(
            row.get("coach_name")
        ).casefold()

        id_match = bool(
            candidate_coach_id
            and verified_id
            and candidate_coach_id
            == verified_id
        )

        name_match = bool(
            candidate_name
            and verified_name
            and candidate_name
            == verified_name
        )

        if id_match or name_match:
            coach_matches.append(row)

    if not coach_matches:
        return {
            "version": (
                "PBK_COACH_SOURCE_AUTHORITY_V1"
            ),
            "status": (
                "VERIFIED_DIFFERENT_COACH"
            ),
            "automatic_promotion": False,
            "candidate_authority": (
                "PROVIDER_CAREER_CANDIDATE"
            ),
        }

    candidate_start = _date(
        candidate.get("valid_from_utc")
    )

    candidate_end = _date(
        candidate.get("valid_to_utc")
    )

    comparisons = []

    conflict = False

    for row in coach_matches:

        verified_start = _date(
            row.get("valid_from_utc")
        )

        verified_end = _date(
            row.get("valid_to_utc")
        )

        start_match = (
            candidate_start
            == verified_start
        )

        end_match = (
            candidate_end
            == verified_end
        )

        if not start_match:
            conflict = True

        if not end_match:
            conflict = True

        comparisons.append(
            {
                "verified_coach_id": _s(
                    row.get("coach_id")
                ),
                "verified_coach_name": _s(
                    row.get("coach_name")
                ),
                "candidate_start": (
                    candidate_start.isoformat()
                    if candidate_start
                    else ""
                ),
                "verified_start": (
                    verified_start.isoformat()
                    if verified_start
                    else ""
                ),
                "candidate_end": (
                    candidate_end.isoformat()
                    if candidate_end
                    else ""
                ),
                "verified_end": (
                    verified_end.isoformat()
                    if verified_end
                    else ""
                ),
                "start_match": start_match,
                "end_match": end_match,
            }
        )

    return {
        "version": (
            "PBK_COACH_SOURCE_AUTHORITY_V1"
        ),
        "status": (
            "PROVIDER_VERIFIED_CONFLICT"
            if conflict
            else "PROVIDER_CORROBORATES_VERIFIED"
        ),
        "candidate_authority": (
            "PROVIDER_CAREER_CANDIDATE"
        ),
        "verified_comparators": (
            comparisons
        ),
        "automatic_promotion": False,
        "historical_verified_created": False,
        "research_only": True,
    }


def resolve_coach_at(
    rows: list[dict[str, Any]],
    *,
    team_id: str,
    as_of_utc: str,
) -> dict[str, Any]:

    candidates = []

    rejected_non_authoritative = 0

    boundary_uncertain = []

    for row in rows:

        if (
            _s(row.get("team_id"))
            != _s(team_id)
        ):
            continue

        if not row_is_authoritative(
            row
        ):
            rejected_non_authoritative += 1
            continue

        state = coverage_state(
            row,
            as_of_utc,
        )

        if (
            state
            == "DATE_BOUNDARY_UNCERTAIN"
        ):
            boundary_uncertain.append(
                dict(row)
            )
            continue

        if state != "COVERED":
            continue

        candidates.append(
            dict(row)
        )

    if (
        not candidates
        and boundary_uncertain
    ):

        return {
            "version": (
                "PBK_COACH_TENURE_CONTRACT_V2"
            ),
            "status": (
                "COACH_TENURE_DATE_BOUNDARY_UNCERTAIN"
            ),
            "team_id": _s(team_id),
            "as_of_utc": as_of_utc,
            "coach": None,
            "candidate_count": 0,
            "boundary_candidates": (
                boundary_uncertain
            ),
            "rejected_non_authoritative": (
                rejected_non_authoritative
            ),
            "no_lookahead": True,
            "research_only": True,
            "operational_betting_authority": False,
        }

    if not candidates:

        return {
            "version": (
                "PBK_COACH_TENURE_CONTRACT_V2"
            ),
            "status": "COACH_UNKNOWN",
            "team_id": _s(team_id),
            "as_of_utc": as_of_utc,
            "coach": None,
            "candidate_count": 0,
            "rejected_non_authoritative": (
                rejected_non_authoritative
            ),
            "no_lookahead": True,
            "research_only": True,
            "operational_betting_authority": False,
        }

    unique = {
        (
            _s(row.get("coach_id")),
            _s(row.get("coach_name")),
            _s(
                row.get(
                    "valid_from_utc"
                )
            ),
            _s(
                row.get(
                    "valid_to_utc"
                )
            ),
        )
        for row in candidates
    }

    if len(unique) != 1:

        return {
            "version": (
                "PBK_COACH_TENURE_CONTRACT_V2"
            ),
            "status": (
                "COACH_TENURE_AMBIGUOUS"
            ),
            "team_id": _s(team_id),
            "as_of_utc": as_of_utc,
            "coach": None,
            "candidate_count": (
                len(candidates)
            ),
            "candidates": candidates,
            "rejected_non_authoritative": (
                rejected_non_authoritative
            ),
            "no_lookahead": True,
            "research_only": True,
            "operational_betting_authority": False,
        }

    selected = candidates[0]

    return {
        "version": (
            "PBK_COACH_TENURE_CONTRACT_V2"
        ),
        "status": "COACH_RESOLVED",
        "team_id": _s(team_id),
        "as_of_utc": as_of_utc,
        "coach": {
            "coach_id": _s(
                selected.get("coach_id")
            ),
            "coach_name": _s(
                selected.get(
                    "coach_name"
                )
            ),
            "valid_from_utc": _s(
                selected.get(
                    "valid_from_utc"
                )
            ),
            "valid_to_utc": _s(
                selected.get(
                    "valid_to_utc"
                )
            ),
            "effective_precision": (
                effective_precision(
                    selected
                )
            ),
            "source_type": _s(
                selected.get(
                    "source_type"
                )
            ),
            "source_ref": _s(
                selected.get(
                    "source_ref"
                )
            ),
            "temporal_authority": _s(
                selected.get(
                    "temporal_authority"
                )
            ),
            "evidence_quality": _s(
                selected.get(
                    "evidence_quality"
                )
            ),
        },
        "candidate_count": 1,
        "rejected_non_authoritative": (
            rejected_non_authoritative
        ),
        "no_lookahead": True,
        "research_only": True,
        "operational_betting_authority": False,
    }
