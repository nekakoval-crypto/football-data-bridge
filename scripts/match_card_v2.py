#!/usr/bin/env python3
"""PBK Match Card v2 public composition layer.

The established Match Card implementation lives in ``match_card_core``. This
module adds Formation/Coach/Expected-XI, factual M5 lineup-surprise context and
the provider-free Player Grade read model without changing the existing
market/probability/canonical contract.
"""
from __future__ import annotations

import match_card_core as _core
from lineup_context import build_lineup_context
from formation_research import read_audit
from lineup_surprise import build_surprise_context
from player_grade_context import build_player_grade_context
from style_matchup_passport import build_style_matchup_passport
from factor_registry import build_factor_registry

CARD_VERSION = _core.CARD_VERSION
MARKET_FAMILY_ORDER = _core.MARKET_FAMILY_ORDER
MARKET_LABELS = _core.MARKET_LABELS


def _lineup_unavailable(fixture_id, error, http_status):
    return {
        "fixture_id": str(fixture_id or ""),
        "available": False,
        "status": "UNKNOWN",
        "no_lookahead": True,
        "coverage": {
            "status": "UNKNOWN",
            "confirmed_teams": 0,
            "usable_teams": 0,
            "limitations": [str(error or "LINEUP_CONTEXT_UNAVAILABLE")],
        },
        "read_only": True,
        "provider_polling": False,
        "creates_signal": False,
        "eligibility_mutation": False,
        "model_mutation": False,
        "source_http_status": http_status,
    }


def _surprise_unavailable(fixture_id, limitation="LINEUP_CONTEXT_UNAVAILABLE"):
    return {
        "fixture_id": str(fixture_id or ""),
        "available": False,
        "status": "UNKNOWN",
        "no_lookahead": True,
        "home": {"available": False, "limitations": [limitation]},
        "away": {"available": False, "limitations": [limitation]},
        "coverage": {
            "status": "UNKNOWN",
            "usable_teams": 0,
            "limitations": [limitation],
        },
        "context_only": True,
        "read_only": True,
        "provider_polling": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "notes": "Factual expected-vs-official XI overlap only; no betting-impact score.",
    }


def _player_grade_unavailable(fixture_id, limitation="LINEUP_CONTEXT_UNAVAILABLE"):
    return {
        "version": "PBK_PLAYER_GRADE_CONTEXT_V1",
        "fixture_id": str(fixture_id or ""),
        "available": False,
        "home": {"grades": [], "player_pool": [], "xi_quality": {"available": False}},
        "away": {"grades": [], "player_pool": [], "xi_quality": {"available": False}},
        "coverage": {"limitations": [limitation]},
        "research_only": True,
        "no_lookahead": True,
        "provider_polling": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def build_match_card(conn, fixture_id):
    """Build Match Card v2 and enrich it with optional research contexts.

    Extensions are additive. Their natural unavailability before enough history
    or official XI publication must not downgrade the established core coverage.
    """
    status, payload = _core.build_match_card(conn, fixture_id)
    if status != 200:
        return status, payload

    lineup_status, lineup = build_lineup_context(conn, fixture_id)
    if lineup_status != 200:
        lineup = _lineup_unavailable(
            fixture_id,
            (lineup or {}).get("error") if isinstance(lineup, dict) else None,
            lineup_status,
        )

    if lineup_status == 200:
        surprise = build_surprise_context(lineup)
        player_grade = build_player_grade_context(conn, fixture_id, lineup)
    else:
        surprise = _surprise_unavailable(fixture_id)
        player_grade = _player_grade_unavailable(fixture_id)

    style_matchup = build_style_matchup_passport(
        conn,
        payload.get("fixture") or {},
    )

    payload["formation_research"] = read_audit(conn, fixture_id=fixture_id)
    payload["lineup_context"] = lineup
    payload["lineup_surprise"] = surprise
    payload["player_grade"] = player_grade
    payload["style_matchup"] = style_matchup
    payload["factor_registry"] = build_factor_registry(payload)

    coverage = payload.setdefault("coverage", {})
    optional = coverage.setdefault("optional_sections", {})
    optional["lineup_context"] = bool(lineup.get("available"))
    optional["lineup_surprise"] = bool(surprise.get("available"))
    optional["player_grade"] = bool(player_grade.get("available"))
    optional["style_matchup"] = bool(style_matchup.get("available"))
    optional["factor_registry"] = True
    extension_limitations = []
    if not lineup.get("available"):
        extension_limitations.append("LINEUP_CONTEXT_UNAVAILABLE")
    if not surprise.get("available"):
        extension_limitations.append("LINEUP_SURPRISE_PENDING_OR_UNAVAILABLE")
    if not player_grade.get("available"):
        extension_limitations.append("PLAYER_GRADE_HISTORY_UNAVAILABLE")
    coverage["extension_limitations"] = extension_limitations

    payload["feature_contract"] = {
        "lineup_context_no_lookahead": bool(lineup.get("no_lookahead", True)),
        "lineup_context_optional": True,
        "lineup_surprise_context_only": True,
        "lineup_surprise_optional_until_official_xi": True,
        "player_grade_research_only": True,
        "player_grade_no_lookahead": bool(player_grade.get("no_lookahead", True)),
        "style_matchup_research_only": True,
        "style_matchup_no_lookahead": bool(style_matchup.get("no_lookahead", True)),
        "style_matchup_validated_claim_allowed": False,
        "matchup_grade_authorized": False,
        "manual_lineup_scenario_what_if_only": True,
        "factor_registry_read_only": True,
        "factor_registry_aggregate_score_authorized": False,
        "factor_registry_double_counting_guard": True,
        "provider_polling": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }
    return 200, payload


def __getattr__(name):
    """Keep existing helper-level imports compatible with the previous module."""
    return getattr(_core, name)
