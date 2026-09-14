#!/usr/bin/env python3
"""Canonical PBK probability/value calculation contract.

This module is intentionally provider-free and strategy-neutral. It centralizes
only arithmetic/projection semantics used by downstream PBK surfaces:

  decimal odds -> implied probability -> no-vig probability -> model edge -> EV
  -> descriptive value rating.

It MUST NOT create a betting signal, change R1/R2/R3 eligibility, change stake,
or infer that an observed bookmaker price was a real bet.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Mapping

CONTRACT_VERSION = "PBK_CALC_V1"

STRONG_VALUE_EV = Decimal("0.05")
STRONG_VALUE_EDGE = Decimal("0.03")
WATCH_VALUE_EV = Decimal("0.02")
WATCH_VALUE_EDGE = Decimal("0.02")
MARKET_DISAGREEMENT_EDGE = Decimal("0.05")
HIGH_PROBABILITY = Decimal("0.65")
LONGSHOT_ODDS = Decimal("2")


def _decimal(value):
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return number if number.is_finite() else None


def probability(value):
    number = _decimal(value)
    return number if number is not None and Decimal("0") < number < Decimal("1") else None


def decimal_odds(value):
    number = _decimal(value)
    return number if number is not None and number > Decimal("1") else None


def implied_probability(odds):
    odds = decimal_odds(odds)
    return None if odds is None else Decimal("1") / odds


def no_vig_probabilities(odds_by_outcome: Mapping[str, object]):
    """Return normalized implied probabilities keyed exactly like the input.

    Any missing/invalid price makes the whole market unavailable. This prevents
    silently normalizing an incomplete market.
    """
    implied = {}
    for outcome, odds in odds_by_outcome.items():
        p = implied_probability(odds)
        if p is None:
            return None
        implied[outcome] = p
    denominator = sum(implied.values(), Decimal("0"))
    if denominator <= 0:
        return None
    return {outcome: value / denominator for outcome, value in implied.items()}


def match_winner_no_vig(home_odds, draw_odds, away_odds, selection):
    probs = no_vig_probabilities({"HOME": home_odds, "DRAW": draw_odds, "AWAY": away_odds})
    if probs is None:
        return None
    normalized = str(selection or "").strip().upper()
    aliases = {
        "H": "HOME", "HOME": "HOME", "1": "HOME", "П1": "HOME",
        "D": "DRAW", "DRAW": "DRAW", "X": "DRAW", "Х": "DRAW",
        "A": "AWAY", "AWAY": "AWAY", "2": "AWAY", "П2": "AWAY",
    }
    wanted = aliases.get(normalized)
    return None if wanted is None else probs[wanted]


def expected_value(model_probability, odds):
    p_model = probability(model_probability)
    price = decimal_odds(odds)
    if p_model is None or price is None:
        return None
    return p_model * price - Decimal("1")


def evaluate_value(model_probability, market_no_vig_probability, odds=None, *, executable=False):
    """Return the canonical descriptive value projection.

    ``executable`` is an upstream evidence flag. When false, odds are ignored and
    no EV-based rating is emitted. Ratings are descriptive only and never alter
    strategy eligibility or stake.
    """
    p_model = probability(model_probability)
    p_market = probability(market_no_vig_probability)
    if p_model is None or p_market is None:
        return None

    price = decimal_odds(odds) if executable else None
    edge = p_model - p_market
    ev = p_model * price - Decimal("1") if price is not None else None

    rating = "NO_VALUE"
    tags = []
    if ev is not None and ev >= STRONG_VALUE_EV and edge >= STRONG_VALUE_EDGE:
        rating = "STRONG_VALUE"
        if price >= LONGSHOT_ODDS:
            tags.append("LONGSHOT_STRONG")
    elif ev is not None and ev >= WATCH_VALUE_EV and edge >= WATCH_VALUE_EDGE:
        rating = "WATCH_VALUE"
    elif ev is None and edge >= MARKET_DISAGREEMENT_EDGE:
        rating = "MARKET_DISAGREEMENT"
    elif ev is not None and p_model >= HIGH_PROBABILITY and ev < WATCH_VALUE_EV:
        rating = "HIGH_PROB_LOW_VALUE"

    return {
        "contract_version": CONTRACT_VERSION,
        "p_model": float(p_model),
        "p_market_no_vig": float(p_market),
        "edge": float(edge),
        "edge_pp": float(edge * Decimal("100")),
        "executable_odds": float(price) if price is not None else None,
        "ev": float(ev) if ev is not None else None,
        "ev_pct": float(ev * Decimal("100")) if ev is not None else None,
        "rating": rating,
        "tags": tags,
        "creates_signal": False,
        "stake_changes": False,
        "eligibility_mutation": False,
    }


def contract_policy():
    return {
        "contract_version": CONTRACT_VERSION,
        "probability_range": "0 < p < 1",
        "decimal_odds_range": "odds > 1",
        "no_vig": "normalize complete market implied probabilities by their sum",
        "ev": "p_model * decimal_odds - 1",
        "rating_is_descriptive_only": True,
        "creates_signal": False,
        "stake_changes": False,
        "eligibility_mutation": False,
    }
