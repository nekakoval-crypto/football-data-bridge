#!/usr/bin/env python3
"""PBK Point14B — evidence-first Expected XI positional resolver.

No calibrated P(start) is fabricated here.

Selection order:
1. explicit availability;
2. positional fit;
3. prior starting usage;
4. recent minutes;
5. prior form.

If no evidence-backed replacement exists, the slot remains unresolved.
"""
from __future__ import annotations

from typing import Any

try:
    from player_expected_xi_availability import resolve_player_availability
except ImportError:
    from scripts.player_expected_xi_availability import resolve_player_availability


POSITION_GROUP = {
    "GK": "G", "G": "G",

    "RB": "D", "RWB": "D", "CB": "D", "LCB": "D", "RCB": "D",
    "LB": "D", "LWB": "D", "D": "D", "DEFENDER": "D",

    "DM": "M", "CDM": "M", "CM": "M", "LCM": "M", "RCM": "M",
    "AM": "M", "CAM": "M", "LM": "M", "RM": "M",
    "M": "M", "MIDFIELDER": "M",

    "RW": "F", "LW": "F", "RF": "F", "LF": "F",
    "ST": "F", "CF": "F", "F": "F", "FW": "F",
    "FORWARD": "F", "ATTACKER": "F",
}


FORMATION_SLOTS = {
    "4-3-3": [
        "GK",
        "RB", "CB", "CB", "LB",
        "CM", "CM", "CM",
        "RW", "ST", "LW",
    ],
    "4-2-3-1": [
        "GK",
        "RB", "CB", "CB", "LB",
        "DM", "DM",
        "RW", "AM", "LW",
        "ST",
    ],
    "4-4-2": [
        "GK",
        "RB", "CB", "CB", "LB",
        "RM", "CM", "CM", "LM",
        "ST", "ST",
    ],
    "3-4-3": [
        "GK",
        "CB", "CB", "CB",
        "RWB", "CM", "CM", "LWB",
        "RW", "ST", "LW",
    ],
    "3-5-2": [
        "GK",
        "CB", "CB", "CB",
        "RWB", "CM", "DM", "CM", "LWB",
        "ST", "ST",
    ],
}


def _s(value: Any) -> str:
    return str(value or "").strip()


def _u(value: Any) -> str:
    return _s(value).upper()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_position(value: Any) -> str:
    token = _u(value).replace(" ", "")

    aliases = {
        "GOALKEEPER": "GK",
        "RIGHTBACK": "RB",
        "RIGHTWINGBACK": "RWB",
        "CENTREBACK": "CB",
        "CENTERBACK": "CB",
        "LEFTBACK": "LB",
        "LEFTWINGBACK": "LWB",
        "DEFENSIVEMIDFIELD": "DM",
        "CENTRALMIDFIELD": "CM",
        "ATTACKINGMIDFIELD": "AM",
        "RIGHTMIDFIELD": "RM",
        "LEFTMIDFIELD": "LM",
        "RIGHTWING": "RW",
        "LEFTWING": "LW",
        "CENTREFORWARD": "ST",
        "CENTERFORWARD": "ST",
        "STRIKER": "ST",
    }

    token = aliases.get(token, token)
    return token if token in POSITION_GROUP else ""


def broad_group(position: Any) -> str:
    return POSITION_GROUP.get(normalize_position(position), "")


def candidate_positions(candidate: dict[str, Any]) -> tuple[str, list[str]]:
    primary = normalize_position(
        candidate.get("primary_position")
        or candidate.get("position")
        or candidate.get("latest_observed_position")
    )

    raw = candidate.get("documented_positions") or []

    if isinstance(raw, str):
        raw = [
            part.strip()
            for part in raw.replace("|", ",").replace(";", ",").split(",")
            if part.strip()
        ]

    documented = []

    for value in raw:
        pos = normalize_position(value)
        if pos and pos not in documented:
            documented.append(pos)

    if primary and primary not in documented:
        documented.insert(0, primary)

    return primary, documented


def positional_fit(candidate: dict[str, Any], slot: str) -> dict[str, Any]:
    slot = normalize_position(slot)
    primary, documented = candidate_positions(candidate)

    if primary == slot:
        level = "PRIMARY_EXACT"
        rank = 4
    elif slot in documented:
        level = "DOCUMENTED_EXACT"
        rank = 3
    elif primary and broad_group(primary) == broad_group(slot):
        level = "PRIMARY_GROUP_ONLY"
        rank = 2
    elif any(broad_group(pos) == broad_group(slot) for pos in documented):
        level = "DOCUMENTED_GROUP_ONLY"
        rank = 1
    else:
        level = "NO_FIT"
        rank = 0

    return {
        "fit_level": level,
        "fit_rank": rank,
        "slot": slot,
        "primary_position": primary,
        "documented_positions": documented,
    }


def resolve_candidate(
    candidate: dict[str, Any],
    *,
    team_id: str,
    target_competition: str,
    before_utc: str,
) -> dict[str, Any]:
    availability = resolve_player_availability(
        candidate.get("availability_events") or [],
        player_id=_s(candidate.get("player_id")),
        team_id=_s(team_id),
        target_competition=target_competition,
        before_utc=before_utc,
    )

    result = dict(candidate)
    result["availability"] = availability
    return result


def candidate_sort_key(
    candidate: dict[str, Any],
    slot: str,
) -> tuple:
    availability = candidate.get("availability") or {}

    availability_rank = {
        "AVAILABLE": 2,
        "UNCERTAIN": 1,
        "UNAVAILABLE": 0,
    }.get(_u(availability.get("availability_status")), 0)

    fit = positional_fit(candidate, slot)

    return (
        availability_rank,
        fit["fit_rank"],
        int(_num(candidate.get("starts_last_10"))),
        int(_num(candidate.get("starts_last_5"))),
        _num(candidate.get("minutes_last_5")),
        _num(candidate.get("form_5"), -999.0),
        _num(candidate.get("form_3"), -999.0),
        _s(candidate.get("player_id")),
    )


def ranked_candidates_for_slot(
    candidates: list[dict[str, Any]],
    *,
    slot: str,
    team_id: str,
    target_competition: str,
    before_utc: str,
    already_selected: set[str] | None = None,
) -> list[dict[str, Any]]:
    selected = already_selected or set()
    rows = []

    for candidate in candidates or []:
        pid = _s(candidate.get("player_id"))

        if not pid or pid in selected:
            continue

        resolved = resolve_candidate(
            candidate,
            team_id=team_id,
            target_competition=target_competition,
            before_utc=before_utc,
        )

        if resolved["availability"]["availability_status"] == "UNAVAILABLE":
            continue

        fit = positional_fit(resolved, slot)

        if fit["fit_rank"] <= 0:
            continue

        resolved["slot_fit"] = fit
        rows.append(resolved)

    rows.sort(
        key=lambda row: candidate_sort_key(row, slot),
        reverse=True,
    )

    return rows


def _slot_candidate_count(
    slot: str,
    candidates: list[dict[str, Any]],
    *,
    team_id: str,
    target_competition: str,
    before_utc: str,
) -> int:
    return len(
        ranked_candidates_for_slot(
            candidates,
            slot=slot,
            team_id=team_id,
            target_competition=target_competition,
            before_utc=before_utc,
        )
    )


def resolve_expected_xi(
    candidates: list[dict[str, Any]],
    *,
    formation: str,
    team_id: str,
    target_competition: str,
    before_utc: str,
) -> dict[str, Any]:

    slots = list(FORMATION_SLOTS.get(_s(formation), []))

    if len(slots) != 11:
        return {
            "version": "PBK_EXPECTED_XI_V1",
            "status": "UNSUPPORTED_FORMATION",
            "formation": formation,
            "expected_xi": [],
            "unresolved_slots": slots,
            "start_probability_authority": "UNCALIBRATED",
            "research_only": True,
        }

    indexed_slots = list(enumerate(slots))

    indexed_slots.sort(
        key=lambda item: (
            _slot_candidate_count(
                item[1],
                candidates,
                team_id=team_id,
                target_competition=target_competition,
                before_utc=before_utc,
            ),
            item[0],
        )
    )

    selected_ids = set()
    assignments = {}
    unresolved = []

    for original_index, slot in indexed_slots:
        ranked = ranked_candidates_for_slot(
            candidates,
            slot=slot,
            team_id=team_id,
            target_competition=target_competition,
            before_utc=before_utc,
            already_selected=selected_ids,
        )

        if not ranked:
            unresolved.append({
                "slot_index": original_index,
                "slot": slot,
                "reason": "NO_EVIDENCE_BACKED_AVAILABLE_CANDIDATE",
            })
            continue

        chosen = ranked[0]
        pid = _s(chosen.get("player_id"))

        selected_ids.add(pid)

        availability = chosen["availability"]
        fit = chosen["slot_fit"]

        assignments[original_index] = {
            "slot_index": original_index,
            "slot": slot,
            "player_id": pid,
            "player_name": _s(chosen.get("player_name")),
            "availability_status": availability["availability_status"],
            "availability_reason": availability["resolution_reason"],
            "fit_level": fit["fit_level"],
            "primary_position": fit["primary_position"],
            "documented_positions": fit["documented_positions"],
            "starts_last_5": int(_num(chosen.get("starts_last_5"))),
            "starts_last_10": int(_num(chosen.get("starts_last_10"))),
            "minutes_last_5": _num(chosen.get("minutes_last_5")),
            "form_3": chosen.get("form_3"),
            "form_5": chosen.get("form_5"),
            "start_probability": None,
            "start_probability_status": "UNCALIBRATED",
        }

    expected_xi = [
        assignments[index]
        for index in range(len(slots))
        if index in assignments
    ]

    uncertain_starters = sum(
        row["availability_status"] == "UNCERTAIN"
        for row in expected_xi
    )

    if unresolved:
        status = "EXPECTED_XI_UNCERTAIN"
    elif uncertain_starters:
        status = "EXPECTED_XI_COMPLETE_WITH_UNCERTAINTY"
    else:
        status = "EXPECTED_XI_COMPLETE"

    return {
        "version": "PBK_EXPECTED_XI_V1",
        "status": status,
        "formation": formation,
        "team_id": _s(team_id),
        "target_competition": target_competition,
        "before_utc": before_utc,
        "expected_xi_count": len(expected_xi),
        "expected_xi": expected_xi,
        "unresolved_slots": sorted(
            unresolved,
            key=lambda row: row["slot_index"],
        ),
        "uncertain_starters": uncertain_starters,
        "start_probability_authority": "UNCALIBRATED",
        "selection_policy": (
            "LEXICOGRAPHIC_AVAILABILITY_THEN_POSITION_FIT_THEN_PRIOR_USAGE_FORM"
        ),
        "mega_score_used": False,
        "no_lookahead": True,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }
