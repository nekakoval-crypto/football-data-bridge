#!/usr/bin/env python3
"""Conservative exact-name profile bridge for Stage92.

Only firstname+lastname from persisted API-Football profile evidence may create
HIGH-authority candidates. Observed display names remain REVIEW-only.
No provider/network calls are made here.
"""
from __future__ import annotations

import unicodedata
from collections import defaultdict
from typing import Any

STRONG_PROFILE_METHOD = "EXACT_FULL_NAME_VIA_API_PROFILE"
SECONDARY_PROFILE_METHOD = "EXACT_OBSERVED_PROFILE_NAME"


def sval(value: Any) -> str:
    return str(value if value is not None else "").strip()


def normalized_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", sval(value))
    text = text.replace("’", "'").replace(chr(96), "'")
    return " ".join(text.casefold().split())


def build_profile_indexes(profile_rows: list[dict[str, str]]):
    strong = defaultdict(dict)
    secondary = defaultdict(dict)

    for row in profile_rows:
        player_id = sval(row.get("player_id"))
        observed = sval(row.get("player_name"))
        firstname = sval(row.get("firstname"))
        lastname = sval(row.get("lastname"))
        if not player_id:
            continue

        if firstname and lastname:
            full_name = f"{firstname} {lastname}"
            strong[normalized_name(full_name)][player_id] = {
                "pbk_player_id": player_id,
                "pbk_player_name": observed or full_name,
                "profile_name": full_name,
            }

        if len(normalized_name(observed).split()) >= 2:
            secondary[normalized_name(observed)][player_id] = {
                "pbk_player_id": player_id,
                "pbk_player_name": observed,
                "profile_name": observed,
            }

    return strong, secondary


def unique_index(grouped):
    return {
        key: next(iter(values.values()))
        for key, values in grouped.items()
        if len(values) == 1
    }


def classify_exact_profile(player_name: str, profile_rows: list[dict[str, str]]):
    strong, secondary = build_profile_indexes(profile_rows)
    strong_match = unique_index(strong).get(normalized_name(player_name))
    secondary_match = unique_index(secondary).get(normalized_name(player_name))

    if (
        strong_match
        and secondary_match
        and strong_match["pbk_player_id"] != secondary_match["pbk_player_id"]
    ):
        return {
            "status": "CONFLICT",
            "method": "CONFLICTING_PROFILE_IDENTITY",
            "confidence": "LOW",
            "authoritative": False,
            "pbk_player_id": "",
            "pbk_player_name": "",
        }

    if strong_match:
        return {
            "status": "AUTO_MATCH",
            "method": STRONG_PROFILE_METHOD,
            "confidence": "HIGH",
            "authoritative": True,
            **strong_match,
        }

    if secondary_match:
        return {
            "status": "REVIEW",
            "method": SECONDARY_PROFILE_METHOD,
            "confidence": "MEDIUM",
            "authoritative": False,
            **secondary_match,
        }

    return None
