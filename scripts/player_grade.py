#!/usr/bin/env python3
"""PBK Player Grade research engine.

This module is deliberately strategy-neutral. It turns already captured player
statistics or event data into transparent research grades. It must never create
or alter canonical signals, probability, eligibility, stake or settlement.

Two source tiers are supported:
* API-Football /fixtures/players: production-friendly aggregate match stats.
* StatsBomb Open Data: provider-free event-level research/prototyping.

The aggregate grade is a PBK score, not the provider's own 0-10 rating.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean

GRADE_VERSION = "PBK_PLAYER_GRADE_V1"

COMPONENTS = (
    "attack", "progression", "creation", "possession",
    "defending", "pressing", "discipline",
)

POSITION_WEIGHTS = {
    "G": {"attack": .02, "progression": .16, "creation": .02, "possession": .18, "defending": .44, "pressing": .02, "discipline": .16},
    "D": {"attack": .06, "progression": .16, "creation": .07, "possession": .14, "defending": .38, "pressing": .10, "discipline": .09},
    "M": {"attack": .11, "progression": .21, "creation": .18, "possession": .18, "defending": .12, "pressing": .12, "discipline": .08},
    "F": {"attack": .34, "progression": .12, "creation": .20, "possession": .10, "defending": .04, "pressing": .12, "discipline": .08},
}


def _num(value, default=0.0):
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _clip(value, low=0.0, high=10.0):
    return max(low, min(high, value))


def _position(value):
    text = str(value or "").strip().upper()
    if text.startswith("G"):
        return "G"
    if text.startswith("D"):
        return "D"
    if text.startswith("F") or text in {"ST", "CF", "LW", "RW"}:
        return "F"
    return "M"


def _rate(value, minutes):
    minutes = max(_num(minutes), 1.0)
    return _num(value) * 90.0 / minutes


def _score(rate, neutral, scale):
    """Map an interpretable per-90 quantity to 0..10 around neutral=5."""
    return _clip(5.0 + (rate - neutral) / max(scale, .01))


def normalize_api_football_player(player, statistics):
    """Flatten one API-Football /fixtures/players player/statistics item."""
    games = statistics.get("games") or {}
    shots = statistics.get("shots") or {}
    goals = statistics.get("goals") or {}
    passes = statistics.get("passes") or {}
    tackles = statistics.get("tackles") or {}
    duels = statistics.get("duels") or {}
    dribbles = statistics.get("dribbles") or {}
    fouls = statistics.get("fouls") or {}
    cards = statistics.get("cards") or {}
    penalty = statistics.get("penalty") or {}
    return {
        "player_id": str((player or {}).get("id") or ""),
        "player_name": (player or {}).get("name"),
        "position": games.get("position"),
        "minutes": games.get("minutes"),
        "provider_rating": games.get("rating"),
        "shots_total": shots.get("total"),
        "shots_on": shots.get("on"),
        "goals": goals.get("total"),
        "assists": goals.get("assists"),
        "passes_total": passes.get("total"),
        "passes_key": passes.get("key"),
        "passes_accuracy": passes.get("accuracy"),
        "tackles_total": tackles.get("total"),
        "tackles_blocks": tackles.get("blocks"),
        "interceptions": tackles.get("interceptions"),
        "duels_total": duels.get("total"),
        "duels_won": duels.get("won"),
        "dribbles_attempts": dribbles.get("attempts"),
        "dribbles_success": dribbles.get("success"),
        "fouls_drawn": fouls.get("drawn"),
        "fouls_committed": fouls.get("committed"),
        "yellow": cards.get("yellow"),
        "red": cards.get("red"),
        "penalty_won": penalty.get("won"),
        "penalty_committed": penalty.get("commited"),
        "penalty_scored": penalty.get("scored"),
        "penalty_missed": penalty.get("missed"),
        "source": "API_FOOTBALL_FIXTURES_PLAYERS",
    }


def grade_aggregate(stats):
    """Compute a transparent aggregate PBK grade from per-match player stats.

    This is intentionally a research proxy until event-level validation exists.
    Missing components are excluded and reduce confidence instead of becoming 0.
    """
    minutes = _num(stats.get("minutes"))
    pos = _position(stats.get("position"))
    if minutes <= 0:
        return {
            "version": GRADE_VERSION, "available": False, "player_id": stats.get("player_id"),
            "limitations": ["NO_MINUTES"], "research_only": True,
            "probability_mutation": False, "eligibility_mutation": False, "stake_changes": False,
        }

    duels_total = _num(stats.get("duels_total"))
    duels_won = _num(stats.get("duels_won"))
    duel_pct = (100.0 * duels_won / duels_total) if duels_total > 0 else None
    passes_total = _num(stats.get("passes_total"))
    pass_acc = stats.get("passes_accuracy")
    if isinstance(pass_acc, str):
        pass_acc = pass_acc.replace("%", "")
    pass_acc = _num(pass_acc, default=-1)

    components = {}
    components["attack"] = _clip(
        5 + 1.20 * _rate(stats.get("goals"), minutes)
        + .55 * _rate(stats.get("shots_on"), minutes)
        + .25 * _rate(stats.get("dribbles_success"), minutes)
        + .35 * _rate(stats.get("penalty_won"), minutes)
        - .65 * _rate(stats.get("penalty_missed"), minutes)
    )
    components["creation"] = _clip(
        5 + .80 * _rate(stats.get("assists"), minutes)
        + .45 * _rate(stats.get("passes_key"), minutes)
        + .12 * _rate(stats.get("fouls_drawn"), minutes)
    )
    if passes_total > 0 or pass_acc >= 0:
        accuracy = 75.0 if pass_acc < 0 else pass_acc
        components["possession"] = _clip(5 + (accuracy - 75.0) / 6.0 + .025 * _rate(passes_total, minutes))
    # API-Football aggregate stats do not expose true progressive passing/carrying.
    # Use a conservative proxy and mark the limitation explicitly.
    if passes_total > 0:
        components["progression"] = _clip(5 + .035 * _rate(passes_total, minutes) + .18 * _rate(stats.get("dribbles_success"), minutes))
    components["defending"] = _clip(
        5 + .32 * _rate(stats.get("tackles_total"), minutes)
        + .38 * _rate(stats.get("interceptions"), minutes)
        + .28 * _rate(stats.get("tackles_blocks"), minutes)
        + (0 if duel_pct is None else (duel_pct - 50.0) / 12.0)
    )
    # True pressures are event-level only; aggregate pressing remains unavailable.
    components["pressing"] = None
    components["discipline"] = _clip(
        6.0 - .28 * _rate(stats.get("fouls_committed"), minutes)
        - 1.00 * _rate(stats.get("yellow"), minutes)
        - 4.00 * _rate(stats.get("red"), minutes)
        - 1.80 * _rate(stats.get("penalty_committed"), minutes)
    )

    available = {k: v for k, v in components.items() if v is not None}
    weights = POSITION_WEIGHTS[pos]
    weight_sum = sum(weights[k] for k in available)
    overall = sum(available[k] * weights[k] for k in available) / weight_sum if weight_sum else None
    coverage = len(available) / len(COMPONENTS)
    minute_factor = min(1.0, minutes / 70.0)
    confidence_score = coverage * minute_factor
    confidence = "HIGH" if confidence_score >= .80 else ("MEDIUM" if confidence_score >= .55 else "LOW")
    limitations = ["AGGREGATE_SOURCE_NO_TRUE_ACTION_QUALITY", "PROGRESSION_PROXY_ONLY", "PRESSING_UNAVAILABLE"]

    return {
        "version": GRADE_VERSION,
        "available": overall is not None,
        "player_id": stats.get("player_id"),
        "player_name": stats.get("player_name"),
        "position_group": pos,
        "minutes": minutes,
        "overall_grade": round(overall, 2) if overall is not None else None,
        "components": {k: (round(v, 2) if v is not None else None) for k, v in components.items()},
        "coverage_pct": round(coverage * 100, 1),
        "confidence": confidence,
        "provider_rating_reference": stats.get("provider_rating"),
        "source": stats.get("source") or "AGGREGATE_UNKNOWN",
        "limitations": limitations,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def grade_statsbomb_events(events, player_id, position=None):
    """Prototype event-level action grading for StatsBomb-style event dictionaries.

    Individual actions are scored on the requested -2..+2 half-step scale. The
    mapping is intentionally explicit and conservative; it is a research seed,
    not a claim to reproduce StatsBomb/Hudl proprietary ratings.
    """
    actions = []
    totals = defaultdict(float)
    for event in events or []:
        player = event.get("player") or {}
        if str(player.get("id") or "") != str(player_id):
            continue
        etype = str((event.get("type") or {}).get("name") or "")
        outcome = None
        score = 0.0
        component = "possession"
        if etype == "Pass":
            outcome = (event.get("pass") or {}).get("outcome")
            completed = not outcome
            under = bool(event.get("under_pressure"))
            end = (event.get("pass") or {}).get("end_location") or []
            start = event.get("location") or []
            progress = (end[0] - start[0]) if len(end) >= 1 and len(start) >= 1 else 0
            score = 0.5 if completed else -0.5
            if completed and progress >= 20:
                score += 0.5
            if completed and len(end) > 0 and end[0] >= 102:
                score += 0.5
            if under and completed:
                score += 0.5
            if not completed and progress >= 20:
                score -= 0.5
            component = "progression" if progress >= 10 else "possession"
        elif etype == "Carry":
            end = (event.get("carry") or {}).get("end_location") or []
            start = event.get("location") or []
            progress = (end[0] - start[0]) if len(end) >= 1 and len(start) >= 1 else 0
            score = 0.5 if progress >= 8 else 0.0
            if progress >= 20:
                score = 1.0
            component = "progression"
        elif etype == "Shot":
            shot = event.get("shot") or {}
            xg = _num(shot.get("statsbomb_xg"))
            outcome = str((shot.get("outcome") or {}).get("name") or "")
            score = 2.0 if outcome == "Goal" else (0.5 if outcome in {"Saved", "Post"} else -0.5)
            if xg >= .35 and outcome not in {"Goal", "Post", "Saved"}:
                score -= 0.5
            component = "attack"
        elif etype in {"Interception", "Ball Recovery", "Clearance", "Block"}:
            score = 1.0
            component = "defending"
        elif etype in {"Pressure", "Counterpress"}:
            score = 0.5
            component = "pressing"
        elif etype in {"Duel", "Dribble"}:
            detail = event.get(etype.lower()) or {}
            outcome = str((detail.get("outcome") or {}).get("name") or "")
            success = outcome in {"Won", "Complete", "Success"} or not outcome
            score = 0.5 if success else -0.5
            component = "attack" if etype == "Dribble" else "defending"
        elif etype in {"Foul Committed", "Bad Behaviour"}:
            score = -1.0
            component = "discipline"
        else:
            continue
        score = round(max(-2.0, min(2.0, score)) * 2) / 2
        totals[component] += score
        actions.append({"event_id": event.get("id"), "type": etype, "component": component, "score": score})

    pos = _position(position)
    comp_scores = {}
    for component in COMPONENTS:
        values = [a["score"] for a in actions if a["component"] == component]
        comp_scores[component] = _clip(5 + mean(values) * 2.0) if values else None
    available = {k: v for k, v in comp_scores.items() if v is not None}
    weights = POSITION_WEIGHTS[pos]
    denom = sum(weights[k] for k in available)
    overall = sum(available[k] * weights[k] for k in available) / denom if denom else None
    return {
        "version": GRADE_VERSION,
        "source": "STATSBOMB_OPEN_DATA_EVENTS",
        "player_id": str(player_id),
        "available": overall is not None,
        "position_group": pos,
        "overall_grade": round(overall, 2) if overall is not None else None,
        "components": {k: (round(v, 2) if v is not None else None) for k, v in comp_scores.items()},
        "action_count": len(actions),
        "actions": actions,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }


def rolling_form(grade_rows, before_utc=None, sizes=(5, 10)):
    """Compute rolling grades using only observations before an optional cutoff."""
    rows = []
    for row in grade_rows or []:
        observed = str(row.get("kickoff_utc") or row.get("observed_at_utc") or "")
        if before_utc and observed and observed >= str(before_utc):
            continue
        if row.get("overall_grade") is None:
            continue
        rows.append(row)
    rows.sort(key=lambda r: str(r.get("kickoff_utc") or r.get("observed_at_utc") or ""), reverse=True)
    result = {}
    for size in sizes:
        sample = rows[:size]
        result[f"form_{size}"] = round(mean(_num(r["overall_grade"]) for r in sample), 2) if sample else None
        result[f"sample_{size}"] = len(sample)
    return result


def xi_quality(xi, grades_by_player):
    values, missing = [], []
    by_line = defaultdict(list)
    for player in xi or []:
        pid = str(player.get("id") or player.get("player_id") or "")
        grade = grades_by_player.get(pid) if grades_by_player else None
        value = grade.get("overall_grade") if isinstance(grade, dict) else grade
        if value is None:
            missing.append(pid)
            continue
        value = _num(value)
        values.append(value)
        by_line[_position(player.get("pos") or player.get("position"))].append(value)
    return {
        "available": bool(values),
        "xi_quality": round(mean(values), 2) if values else None,
        "covered_players": len(values),
        "missing_player_ids": missing,
        "coverage_pct": round(100 * len(values) / max(len(xi or []), 1), 1),
        "by_line": {line: round(mean(vals), 2) for line, vals in by_line.items()},
        "research_only": True,
    }
