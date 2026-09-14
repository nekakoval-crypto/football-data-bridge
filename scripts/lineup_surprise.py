#!/usr/bin/env python3
"""PBK M5 lineup surprise / concentration context.

This module is deliberately descriptive. It compares a deterministic expected XI
with a confirmed official XI and reports factual overlap/change metrics. It does
not assign betting impact, change probability, eligibility, stake, Value Radar,
Forward or settlement state.
"""
from __future__ import annotations

import math

CORE_SHARE_THRESHOLD = 0.60


def _ids(items):
    output = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        if pid:
            output.append(pid)
    return output


def _player_map(items):
    return {str(item.get("id")): item for item in (items or []) if isinstance(item, dict) and item.get("id") not in (None, "")}


def _concentration(expected):
    xi = (expected or {}).get("xi") or []
    if len(xi) != 11:
        return {
            "available": False,
            "history_sample": 0,
            "stable_core_players": None,
            "average_start_share_pct": None,
            "threshold": CORE_SHARE_THRESHOLD,
        }
    samples = []
    shares = []
    stable = 0
    for player in xi:
        try:
            starts = int(player.get("historical_starts"))
            sample = int(player.get("history_sample"))
        except (TypeError, ValueError):
            continue
        if sample <= 0 or starts < 0:
            continue
        share = min(1.0, max(0.0, starts / sample))
        samples.append(sample)
        shares.append(share)
        if share >= CORE_SHARE_THRESHOLD:
            stable += 1
    if len(shares) != 11:
        return {
            "available": False,
            "history_sample": max(samples) if samples else 0,
            "stable_core_players": None,
            "average_start_share_pct": None,
            "threshold": CORE_SHARE_THRESHOLD,
        }
    return {
        "available": True,
        "history_sample": max(samples),
        "stable_core_players": stable,
        "average_start_share_pct": round(sum(shares) / len(shares) * 100.0, 1),
        "threshold": CORE_SHARE_THRESHOLD,
    }


def analyze_team(team):
    team = team or {}
    official = team.get("official") or {}
    expected = team.get("expected") or {}
    official_xi = official.get("xi") or []
    expected_xi = expected.get("xi") or []
    official_ids = _ids(official_xi)
    expected_ids = _ids(expected_xi)
    concentration = _concentration(expected)
    limitations = []
    if len(expected_ids) != 11:
        limitations.append("EXPECTED_XI_UNAVAILABLE")
    if len(official_ids) != 11:
        limitations.append("OFFICIAL_XI_UNAVAILABLE")
    if limitations:
        return {
            "available": False,
            "official_confirmed": len(official_ids) == 11,
            "expected_available": len(expected_ids) == 11,
            "overlap_starters": None,
            "unexpected_starters_count": None,
            "missing_expected_count": None,
            "unexpected_starters": [],
            "missing_expected": [],
            "concentration": concentration,
            "limitations": limitations,
        }
    official_set, expected_set = set(official_ids), set(expected_ids)
    overlap = len(official_set & expected_set)
    official_map = _player_map(official_xi)
    expected_map = _player_map(expected_xi)
    unexpected_ids = [pid for pid in official_ids if pid not in expected_set]
    missing_ids = [pid for pid in expected_ids if pid not in official_set]
    return {
        "available": True,
        "official_confirmed": True,
        "expected_available": True,
        "overlap_starters": overlap,
        "unexpected_starters_count": 11 - overlap,
        "missing_expected_count": 11 - overlap,
        "unexpected_starters": [official_map[pid] for pid in unexpected_ids],
        "missing_expected": [expected_map[pid] for pid in missing_ids],
        "concentration": concentration,
        "limitations": [],
    }


def build_surprise_context(lineup_payload):
    lineup_payload = lineup_payload or {}
    home = analyze_team(lineup_payload.get("home"))
    away = analyze_team(lineup_payload.get("away"))
    usable = int(home["available"]) + int(away["available"])
    limitations = []
    if not home["available"]:
        limitations.append("HOME_SURPRISE_UNAVAILABLE")
    if not away["available"]:
        limitations.append("AWAY_SURPRISE_UNAVAILABLE")
    status = "AVAILABLE" if usable == 2 else ("PARTIAL" if usable else "UNKNOWN")
    return {
        "fixture_id": lineup_payload.get("fixture_id"),
        "available": usable > 0,
        "status": status,
        "no_lookahead": bool(lineup_payload.get("no_lookahead", True)),
        "home": home,
        "away": away,
        "coverage": {"status": status, "usable_teams": usable, "limitations": limitations},
        "context_only": True,
        "read_only": True,
        "provider_polling": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "notes": "Factual expected-vs-official XI overlap only; no betting-impact score.",
    }
