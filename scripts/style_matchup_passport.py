#!/usr/bin/env python3
"""Stage96 — Style/Matchup passport eligibility context."""

from __future__ import annotations

import json
from typing import Any


READINESS_DOC = "team_style_validation_readiness.json"
STATISTICS_DOC = (
    "team_style_dimension_validation_statistics.json"
)
MATCHUP_GATE_DOC = "matchup_validation_gate.json"

READINESS_VERSION = (
    "PBK_STAGE93_STYLE_VALIDATION_READINESS_V1"
)
STATISTICS_VERSION = (
    "PBK_STAGE94_STYLE_DIMENSION_VALIDATION_STATISTICS_V1"
)
MATCHUP_GATE_VERSION = (
    "PBK_STAGE95_MATCHUP_VALIDATION_GATE_V1"
)


def _table_exists(conn, table: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        is not None
    )


def _state_doc(conn, name: str) -> Any:
    if not _table_exists(
        conn,
        "state_documents",
    ):
        return None

    row = conn.execute(
        "SELECT payload_json "
        "FROM state_documents "
        "WHERE name=?",
        (name,),
    ).fetchone()

    if row is None:
        return None

    try:
        if hasattr(row, "keys"):
            raw = row["payload_json"]
        else:
            raw = row[0]

        return json.loads(raw)
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None


def _scope_matches(
    row: dict[str, Any],
    fixture: dict[str, Any],
) -> bool:
    league_id = str(
        fixture.get("provider_league_id") or ""
    ).strip()

    season = str(
        fixture.get("season") or ""
    ).strip()

    return (
        str(row.get("league_id") or "").strip()
        == league_id
        and str(row.get("season") or "").strip()
        == season
    )


def build_style_matchup_passport(
    conn,
    fixture: dict[str, Any],
) -> dict[str, Any]:

    readiness = _state_doc(
        conn,
        READINESS_DOC,
    )
    statistics = _state_doc(
        conn,
        STATISTICS_DOC,
    )
    matchup_gate = _state_doc(
        conn,
        MATCHUP_GATE_DOC,
    )

    readiness_groups = []

    if (
        isinstance(readiness, dict)
        and str(readiness.get("version") or "")
        == READINESS_VERSION
    ):
        readiness_groups = [
            row
            for row in readiness.get("groups") or []
            if isinstance(row, dict)
            and _scope_matches(row, fixture)
        ]

    statistics_groups = []

    if (
        isinstance(statistics, dict)
        and str(statistics.get("version") or "")
        == STATISTICS_VERSION
    ):
        statistics_groups = [
            row
            for row in statistics.get("groups") or []
            if isinstance(row, dict)
            and _scope_matches(row, fixture)
        ]

    gate_valid = (
        isinstance(matchup_gate, dict)
        and str(
            matchup_gate.get("version") or ""
        )
        == MATCHUP_GATE_VERSION
    )

    ready_dimensions = sorted(
        {
            str(row.get("dimension") or "")
            for row in readiness_groups
            if (
                str(
                    row.get("readiness_status")
                    or ""
                )
                == "READY"
                and row.get("dimension")
            )
        }
    )

    evidence_dimensions = sorted(
        {
            str(row.get("dimension") or "")
            for row in statistics_groups
            if (
                str(
                    row.get("validation_status")
                    or ""
                )
                == "VALIDATION_EVIDENCE_AVAILABLE"
                and row.get("dimension")
            )
        }
    )

    available = bool(
        readiness_groups
        or statistics_groups
        or gate_valid
    )

    if evidence_dimensions:
        style_status = (
            "VALIDATION_EVIDENCE_AVAILABLE"
        )
    elif ready_dimensions:
        style_status = (
            "READY_FOR_VALIDATION"
        )
    else:
        style_status = "DATA_WAITING"

    matchup_status = (
        str(matchup_gate.get("status") or "")
        if gate_valid
        else "DATA_WAITING"
    )

    return {
        "version": (
            "PBK_STAGE96_STYLE_MATCHUP_PASSPORT_V1"
        ),
        "available": available,
        "fixture_scope": {
            "fixture_id": fixture.get(
                "fixture_id"
            ),
            "provider_league_id": fixture.get(
                "provider_league_id"
            ),
            "league_name": fixture.get(
                "league_name"
            ),
            "season": fixture.get("season"),
            "kickoff_utc": fixture.get(
                "kickoff_utc"
            ),
        },
        "style_validation": {
            "status": style_status,
            "ready_dimensions": ready_dimensions,
            "validation_evidence_dimensions": (
                evidence_dimensions
            ),
            "automatic_validation_decision": False,
            "validated_style_claim_allowed": False,
        },
        "matchup_validation": {
            "status": matchup_status,
            "components_with_required_evidence": (
                matchup_gate.get(
                    "components_with_required_evidence"
                )
                if gate_valid
                else 0
            ),
            "total_components": (
                matchup_gate.get(
                    "total_components"
                )
                if gate_valid
                else 0
            ),
            "matchup_grade_authorized": False,
            "overall_edge_authorized": False,
            "validated_matchup_claim_allowed": False,
        },
        "passport_context_allowed": True,
        "research_only": True,
        "no_lookahead": True,
        "provider_polling": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "r1_r2_r3_mutation": False,
    }
