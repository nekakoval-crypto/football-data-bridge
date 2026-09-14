#!/usr/bin/env python3
"""PBK Match Card v2 public composition layer.

The established Match Card implementation lives in ``match_card_core``. This
module adds Formation/Coach/Expected-XI and factual M5 lineup-surprise context
without changing the existing market/probability/canonical contract.
"""
from __future__ import annotations

import match_card_core as _core
from lineup_context import build_lineup_context
from lineup_surprise import build_surprise_context

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


def build_match_card(conn, fixture_id):
    """Build Match Card v2 and enrich it with optional no-lookahead lineup context.

    Both lineup extensions are additive. Their natural unavailability before
    enough history / official XI publication must not downgrade the established
    Match Card core coverage contract.
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
    else:
        surprise = _surprise_unavailable(fixture_id)

    payload["lineup_context"] = lineup
    payload["lineup_surprise"] = surprise

    coverage = payload.setdefault("coverage", {})
    optional = coverage.setdefault("optional_sections", {})
    optional["lineup_context"] = bool(lineup.get("available"))
    optional["lineup_surprise"] = bool(surprise.get("available"))
    extension_limitations = []
    if not lineup.get("available"):
        extension_limitations.append("LINEUP_CONTEXT_UNAVAILABLE")
    if not surprise.get("available"):
        extension_limitations.append("LINEUP_SURPRISE_PENDING_OR_UNAVAILABLE")
    coverage["extension_limitations"] = extension_limitations

    payload["feature_contract"] = {
        "lineup_context_no_lookahead": bool(lineup.get("no_lookahead", True)),
        "lineup_context_optional": True,
        "lineup_surprise_context_only": True,
        "lineup_surprise_optional_until_official_xi": True,
        "provider_polling": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }
    return 200, payload


def __getattr__(name):
    """Keep existing helper-level imports compatible with the previous module."""
    return getattr(_core, name)
