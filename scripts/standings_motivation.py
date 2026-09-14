#!/usr/bin/env python3
"""Deterministic pre-match standings motivation context.

Provider-free and model-isolated. Only one immutable standings snapshot that
existed at or before fixture kickoff may be used. Unknown competition-format
facts remain UNKNOWN rather than being guessed.
"""
from __future__ import annotations

from datetime import datetime, timezone

import standings_format_registry as format_registry

EUROPE_TYPES = {
    "CHAMPIONS_LEAGUE", "EUROPA_LEAGUE", "CONFERENCE_LEAGUE",
    "EUROPE_GENERIC", "EUROPE_PLAYOFF",
}
ADVERSE_TYPES = {"RELEGATION", "RELEGATION_PLAYOFF"}
PLAYOFF_TYPES = {"CHAMPIONSHIP_PLAYOFF"}
RESOLVED_STATUSES = {
    "POINTS_CLINCHED", "POINTS_SECURED", "POINTS_SAFE",
    "RELEGATED_ON_POINTS", "ELIMINATED",
}
PRESSURE_ORDER = {"UNKNOWN": -1, "NONE_VERIFIED": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


def _text(value):
    return str(value or "").strip()


def _int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _utc(value):
    try:
        parsed = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def description_objectives(description):
    """Normalize only provider text we can recognize conservatively."""
    raw = _text(description)
    if not raw:
        return []
    lower = raw.casefold()
    found = []
    if "champions league" in lower:
        found.append("CHAMPIONS_LEAGUE")
    if "europa league" in lower:
        found.append("EUROPA_LEAGUE")
    if "conference league" in lower:
        found.append("CONFERENCE_LEAGUE")
    if "europe" in lower and not any(item in found for item in EUROPE_TYPES):
        found.append("EUROPE_GENERIC")
    if ("europe" in lower or any(item in found for item in EUROPE_TYPES)) and (
            "play-off" in lower or "playoff" in lower):
        found.append("EUROPE_PLAYOFF")
    if "relegation" in lower:
        if "play-off" in lower or "playoff" in lower:
            found.append("RELEGATION_PLAYOFF")
        else:
            found.append("RELEGATION")
    if ("play-off" in lower or "playoff" in lower) and not any(
            item in found for item in EUROPE_TYPES | ADVERSE_TYPES):
        found.append("CHAMPIONSHIP_PLAYOFF")
    return list(dict.fromkeys(found))


def _rank(row):
    return _int(row.get("rank"))


def _points(row):
    return _int(row.get("points"))


def _played(row):
    return _int(row.get("played"))


def _same_group(rows, group_name):
    group = _text(group_name)
    if not group:
        return [row for row in rows if not _text(row.get("group_name"))] or list(rows)
    return [row for row in rows if _text(row.get("group_name")) == group]


def _find_team(rows, team_id=None, team_name=None):
    tid = _text(team_id)
    if tid:
        matches = [row for row in rows if _text(row.get("team_id")) == tid]
        if len(matches) == 1:
            return matches[0], "TEAM_ID"
        if len(matches) > 1:
            return None, "AMBIGUOUS"
    name = _text(team_name).casefold()
    if name:
        matches = [row for row in rows if _text(row.get("team_name")).casefold() == name]
        if len(matches) == 1:
            return matches[0], "EXACT_NAME"
        if len(matches) > 1:
            return None, "AMBIGUOUS"
    return None, "MISSING"


def format_context(format_meta, played):
    meta = format_meta or {}
    status = _text(meta.get("status")).upper() or "UNKNOWN"
    total = _int(meta.get("total_games"))
    if status not in {"VERIFIED", "DERIVED_SAFE"} or total is None or total <= 0:
        return {
            "total_games": None, "matches_remaining": None,
            "format_status": "UNKNOWN",
            "format_reason": meta.get("reason") or "No verified competition format",
        }
    remaining = None if played is None else max(total - played, 0)
    return {
        "total_games": total, "matches_remaining": remaining,
        "format_status": status,
        "format_reason": meta.get("reason") or "Verified competition format",
    }


def season_phase(played, total_games):
    if played is None or not total_games:
        return "UNKNOWN"
    progress = played / total_games
    if progress < 0.40:
        return "EARLY"
    if progress < 0.70:
        return "MID"
    if progress < 0.90:
        return "LATE"
    return "RUN_IN"


def _max_points(row, total_games):
    points, played = _points(row), _played(row)
    if points is None or played is None or not total_games:
        return None
    return points + 3 * max(total_games - played, 0)


def _title_objective(team, group_rows, total_games):
    ranked = [row for row in group_rows if _rank(row) is not None and _points(row) is not None]
    if not ranked:
        return None
    leader = min(ranked, key=_rank)
    team_points, leader_points = _points(team), _points(leader)
    if team_points is None or leader_points is None:
        return None
    gap = max(leader_points - team_points, 0)
    rank = _rank(team)
    status = "LEADING" if rank == _rank(leader) else "UNKNOWN"
    if total_games:
        team_max = _max_points(team, total_games)
        if rank == _rank(leader):
            rival_max = [_max_points(row, total_games) for row in ranked if row is not leader]
            rival_max = [value for value in rival_max if value is not None]
            status = "POINTS_CLINCHED" if rival_max and team_points > max(rival_max) else "LEADING"
        elif team_max is not None:
            status = "ELIMINATED" if team_max < leader_points else "IN_RACE"
    return {
        "type": "TITLE", "status": status, "gap_points": gap,
        "target_rank": _rank(leader), "target_points": leader_points,
    }


def _zone_objective(team, group_rows, zone_types, objective_type, total_games):
    zone_rows = []
    for row in group_rows:
        kinds = [item for item in description_objectives(row.get("description")) if item in zone_types]
        if kinds and _rank(row) is not None and _points(row) is not None:
            zone_rows.append((row, kinds))
    if not zone_rows:
        return None
    boundary_row, boundary_kinds = max(zone_rows, key=lambda item: _rank(item[0]))
    boundary_rank, boundary_points = _rank(boundary_row), _points(boundary_row)
    team_rank, team_points = _rank(team), _points(team)
    if team_rank is None or team_points is None:
        return None
    own = [item for item in description_objectives(team.get("description")) if item in zone_types]
    typ = own[0] if own else (objective_type or boundary_kinds[0])
    in_zone = team_rank <= boundary_rank and bool(own)
    status = "IN_ZONE" if in_zone else "UNKNOWN"
    gap = 0 if in_zone else max(boundary_points - team_points, 0)
    if total_games:
        team_max = _max_points(team, total_games)
        outside = [row for row in group_rows if (_rank(row) or 10**9) > boundary_rank]
        outside_max = [_max_points(row, total_games) for row in outside]
        outside_max = [value for value in outside_max if value is not None]
        if in_zone and outside_max and team_points > max(outside_max):
            status = "POINTS_SECURED"
        elif not in_zone and team_max is not None:
            status = "ELIMINATED" if team_max < boundary_points else "IN_RACE"
    return {
        "type": typ, "status": status, "gap_points": gap,
        "target_rank": boundary_rank, "target_points": boundary_points,
    }


def _europe_objective(team, group_rows, total_games):
    return _zone_objective(team, group_rows, EUROPE_TYPES, None, total_games)


def _playoff_objective(team, group_rows, total_games):
    return _zone_objective(
        team, group_rows, PLAYOFF_TYPES, "CHAMPIONSHIP_PLAYOFF", total_games)


def _relegation_objective(team, group_rows, total_games):
    adverse = []
    for row in group_rows:
        kinds = description_objectives(row.get("description"))
        kind = "RELEGATION_PLAYOFF" if "RELEGATION_PLAYOFF" in kinds else (
            "RELEGATION" if "RELEGATION" in kinds else None)
        if kind and _rank(row) is not None and _points(row) is not None:
            adverse.append((row, kind))
    if not adverse:
        return None
    first_adverse_rank = min(_rank(row) for row, _ in adverse)
    safe_rows = [row for row in group_rows if _rank(row) is not None and _rank(row) < first_adverse_rank]
    safe_boundary = max(safe_rows, key=_rank) if safe_rows else None
    if safe_boundary is None or _points(safe_boundary) is None:
        return None
    team_rank, team_points = _rank(team), _points(team)
    if team_rank is None or team_points is None:
        return None
    own_kinds = description_objectives(team.get("description"))
    zone_state = None
    if "RELEGATION" in own_kinds:
        zone_state = "IN_RELEGATION_ZONE"
    elif "RELEGATION_PLAYOFF" in own_kinds:
        zone_state = "IN_RELEGATION_PLAYOFF"
    safe_points = _points(safe_boundary)
    adverse_points = [value for value in (_points(row) for row, _ in adverse) if value is not None]
    best_adverse_points = max(adverse_points) if adverse_points else safe_points
    gap = max(safe_points - team_points, 0) if zone_state else max(team_points - best_adverse_points, 0)
    status = zone_state or ("AT_RISK" if gap <= 6 else "UNKNOWN")
    if total_games:
        team_max = _max_points(team, total_games)
        adverse_max = [_max_points(row, total_games) for row, _ in adverse]
        adverse_max = [value for value in adverse_max if value is not None]
        if zone_state and team_max is not None:
            status = "RELEGATED_ON_POINTS" if team_max < safe_points else "CAN_ESCAPE"
        elif adverse_max and team_points > max(adverse_max):
            status = "POINTS_SAFE"
        elif gap <= 6:
            status = "AT_RISK"
    objective_type = "SURVIVAL" if not zone_state else (
        "RELEGATION_PLAYOFF" if zone_state == "IN_RELEGATION_PLAYOFF" else "RELEGATION")
    return {
        "type": objective_type, "status": status, "zone_state": zone_state,
        "gap_points": gap, "target_rank": _rank(safe_boundary),
        "target_points": safe_points,
    }


def _pressure(objectives, phase):
    reasons = []
    strong = False
    relevant = False
    adverse_zone = False
    for objective in objectives:
        typ, status = objective.get("type"), objective.get("status")
        gap = objective.get("gap_points")
        zone_state = objective.get("zone_state")
        if zone_state in {"IN_RELEGATION_ZONE", "IN_RELEGATION_PLAYOFF"}:
            reasons.append(zone_state)
        if status in RESOLVED_STATUSES:
            continue
        if zone_state in {"IN_RELEGATION_ZONE", "IN_RELEGATION_PLAYOFF"}:
            strong = True
            adverse_zone = True
        if typ == "TITLE" and status in {"LEADING", "IN_RACE"} and gap is not None:
            reasons.append(f"TITLE_GAP_{gap}")
            strong = strong or gap <= 3
            relevant = relevant or gap <= 6
        if typ in EUROPE_TYPES and status in {"IN_ZONE", "IN_RACE"}:
            reasons.append(f"EUROPE_BOUNDARY_GAP_{gap if gap is not None else 'UNKNOWN'}")
            strong = strong or (gap is not None and gap <= 3)
            relevant = relevant or (gap is not None and gap <= 6)
        if typ in PLAYOFF_TYPES and status in {"IN_ZONE", "IN_RACE"}:
            reasons.append(f"PLAYOFF_BOUNDARY_GAP_{gap if gap is not None else 'UNKNOWN'}")
            strong = strong or (gap is not None and gap <= 3)
            relevant = relevant or (gap is not None and gap <= 6)
        if typ in {"SURVIVAL", "RELEGATION", "RELEGATION_PLAYOFF"} and gap is not None:
            if zone_state:
                reasons.append(f"WITHIN_{gap}_OF_SURVIVAL")
            strong = strong or gap <= 3
            relevant = relevant or gap <= 6
    if phase == "RUN_IN":
        reasons.append("RUN_IN_PHASE")
    elif phase == "LATE":
        reasons.append("LATE_PHASE")
    if strong and phase in {"LATE", "RUN_IN"}:
        return "HIGH", list(dict.fromkeys(reasons))
    if strong and phase == "UNKNOWN":
        return ("MEDIUM" if adverse_zone else "LOW"), list(dict.fromkeys(reasons))
    if strong:
        return "MEDIUM", list(dict.fromkeys(reasons))
    if relevant and phase in {"LATE", "RUN_IN"}:
        return "MEDIUM", list(dict.fromkeys(reasons))
    if relevant:
        return "LOW", list(dict.fromkeys(reasons))
    verified = [obj for obj in objectives if obj.get("status") not in {None, "UNKNOWN"} | RESOLVED_STATUSES]
    return ("LOW" if verified else "NONE_VERIFIED"), list(dict.fromkeys(reasons))


def _neighbor_facts(team, group_rows):
    ranked = sorted(
        [row for row in group_rows if _rank(row) is not None],
        key=lambda row: (_rank(row), _text(row.get("team_id"))),
    )
    index = next((i for i, row in enumerate(ranked) if row is team), None)
    points = _points(team)
    if index is None or points is None:
        return {"points_to_previous_rank": None, "points_to_next_rank": None}
    previous = ranked[index - 1] if index > 0 else None
    next_row = ranked[index + 1] if index + 1 < len(ranked) else None
    previous_points = _points(previous) if previous else None
    next_points = _points(next_row) if next_row else None
    return {
        "points_to_previous_rank": None if previous_points is None else max(previous_points - points, 0),
        "points_to_next_rank": None if next_points is None else max(points - next_points, 0),
    }


def _objective_gap(objectives, types):
    values = [obj.get("gap_points") for obj in objectives if obj.get("type") in types]
    values = [value for value in values if isinstance(value, int)]
    return min(values) if values else None


def _team_context(team, group_rows, format_meta):
    played = _played(team)
    fmt = format_context(format_meta, played)
    phase = season_phase(played, fmt["total_games"])
    objectives = []
    for candidate in (
            _title_objective(team, group_rows, fmt["total_games"]),
            _europe_objective(team, group_rows, fmt["total_games"]),
            _playoff_objective(team, group_rows, fmt["total_games"]),
            _relegation_objective(team, group_rows, fmt["total_games"])):
        if candidate:
            objectives.append(candidate)
    pressure, reasons = _pressure(objectives, phase)
    if fmt["format_status"] == "UNKNOWN":
        reasons.append("FORMAT_UNKNOWN")
    priority = {
        "RELEGATION": 0, "RELEGATION_PLAYOFF": 0, "SURVIVAL": 0,
        "TITLE": 1, "CHAMPIONS_LEAGUE": 2, "EUROPA_LEAGUE": 3,
        "CONFERENCE_LEAGUE": 3, "EUROPE_GENERIC": 3,
        "EUROPE_PLAYOFF": 4, "CHAMPIONSHIP_PLAYOFF": 5,
    }
    active = [obj for obj in objectives if obj.get("status") not in {"UNKNOWN"} | RESOLVED_STATUSES]
    primary = min(active, key=lambda obj: priority.get(obj.get("type"), 99))["type"] if active else "NO_VERIFIED_TABLE_OBJECTIVE"
    standings = {key: team.get(key) for key in (
        "team_id", "team_name", "rank", "points", "played", "win", "draw", "lose",
        "goals_for", "goals_against", "goals_diff", "form", "group_name", "description")}
    standings["provider_description"] = standings.pop("description", None)
    leader = min([row for row in group_rows if _rank(row) is not None], key=_rank, default=None)
    standings["points_to_first"] = (
        None if leader is None or _points(team) is None or _points(leader) is None
        else max(_points(leader) - _points(team), 0)
    )
    standings.update(_neighbor_facts(team, group_rows))
    standings["points_to_europe_boundary"] = _objective_gap(objectives, EUROPE_TYPES)
    standings["points_to_survival_boundary"] = _objective_gap(
        objectives, {"SURVIVAL", "RELEGATION", "RELEGATION_PLAYOFF"})
    standings["points_to_playoff_boundary"] = _objective_gap(objectives, PLAYOFF_TYPES)
    all_gaps = [obj.get("gap_points") for obj in objectives if isinstance(obj.get("gap_points"), int)]
    standings["points_to_relevant_boundary"] = min(all_gaps) if all_gaps else None
    return {
        "standings": standings, "objectives": objectives, "season_phase": phase,
        "pressure": pressure, "primary_context": primary,
        "reason_codes": list(dict.fromkeys(reasons)), "format": fmt,
    }


def _empty_payload(fixture, limitation):
    return {
        "fixture_id": _text(fixture.get("fixture_id")) or None,
        "provider_league_id": _text(fixture.get("provider_league_id")) or None,
        "season": _text(fixture.get("season")) or None,
        "kickoff_utc": fixture.get("kickoff_utc"),
        "available": False,
        "no_lookahead": True,
        "standings_context": {
            "requested_as_of_utc": fixture.get("kickoff_utc"),
            "snapshot_id": None, "snapshot_observed_at_utc": None,
            "age_seconds_at_cutoff": None, "no_lookahead": True,
        },
        "home": None, "away": None,
        "comparison": {
            "rank_gap": None, "points_gap": None,
            "home_pressure": "UNKNOWN", "away_pressure": "UNKNOWN",
            "asymmetry": "UNKNOWN",
        },
        "coverage": {
            "available": False, "status": "UNKNOWN",
            "format_status": "UNKNOWN", "motivation_status": "UNKNOWN",
            "limitations": [limitation],
        },
    }


def analyze_fixture(fixture, snapshot_rows, format_meta=None):
    """Build auditable motivation context from one eligible pre-match snapshot."""
    if not snapshot_rows:
        return _empty_payload(fixture, "NO_STANDINGS_SNAPSHOT")
    kickoff = _utc(fixture.get("kickoff_utc"))
    snapshot_ids = {_text(row.get("snapshot_id")) for row in snapshot_rows if _text(row.get("snapshot_id"))}
    observed_values = {_text(row.get("observed_at_utc")) for row in snapshot_rows if _text(row.get("observed_at_utc"))}
    if len(snapshot_ids) != 1 or len(observed_values) != 1:
        return _empty_payload(fixture, "SNAPSHOT_INTEGRITY_ERROR")
    observed = _utc(next(iter(observed_values)))
    if kickoff is None or observed is None:
        return _empty_payload(fixture, "SNAPSHOT_INTEGRITY_ERROR")
    if observed > kickoff:
        return _empty_payload(fixture, "LOOKAHEAD_FORBIDDEN")

    home, home_match = _find_team(snapshot_rows, fixture.get("home_team_id"), fixture.get("home_team"))
    away, away_match = _find_team(snapshot_rows, fixture.get("away_team_id"), fixture.get("away_team"))
    if not home or not away:
        return _empty_payload(fixture, "TEAM_NOT_FOUND")
    if _text(home.get("group_name")) != _text(away.get("group_name")):
        return _empty_payload(fixture, "GROUP_AMBIGUOUS")
    group_rows = _same_group(snapshot_rows, home.get("group_name"))
    if home not in group_rows or away not in group_rows:
        return _empty_payload(fixture, "GROUP_AMBIGUOUS")

    effective_format = format_meta if format_meta is not None else format_registry.get_format(
        fixture.get("provider_league_id"), fixture.get("season"))
    home_ctx = _team_context(home, group_rows, effective_format)
    away_ctx = _team_context(away, group_rows, effective_format)
    limitations = []
    if home_ctx["format"]["format_status"] == "UNKNOWN":
        limitations.append("FORMAT_UNKNOWN")
    has_zone = any(description_objectives(row.get("description")) for row in group_rows)
    if not has_zone:
        limitations.append("ZONE_DESCRIPTION_UNKNOWN")
    if home_match == "EXACT_NAME" or away_match == "EXACT_NAME":
        limitations.append("TEAM_ID_MISSING_NAME_MATCH")
    coverage_status = "PARTIAL" if limitations else "AVAILABLE"
    format_status = home_ctx["format"]["format_status"]
    rank_gap = None if _rank(home) is None or _rank(away) is None else _rank(home) - _rank(away)
    points_gap = None if _points(home) is None or _points(away) is None else _points(home) - _points(away)
    hp, ap = home_ctx["pressure"], away_ctx["pressure"]
    if PRESSURE_ORDER[hp] > PRESSURE_ORDER[ap]:
        asymmetry = "HOME_HIGHER"
    elif PRESSURE_ORDER[ap] > PRESSURE_ORDER[hp]:
        asymmetry = "AWAY_HIGHER"
    elif hp == "UNKNOWN":
        asymmetry = "UNKNOWN"
    else:
        asymmetry = "BALANCED"
    return {
        "fixture_id": _text(fixture.get("fixture_id")) or None,
        "provider_league_id": _text(fixture.get("provider_league_id")) or None,
        "season": _text(fixture.get("season")) or None,
        "kickoff_utc": fixture.get("kickoff_utc"),
        "available": True,
        "no_lookahead": True,
        "standings_context": {
            "requested_as_of_utc": fixture.get("kickoff_utc"),
            "snapshot_id": next(iter(snapshot_ids)),
            "snapshot_observed_at_utc": observed.isoformat().replace("+00:00", "Z"),
            "age_seconds_at_cutoff": (kickoff - observed).total_seconds(),
            "no_lookahead": True,
        },
        "home": home_ctx,
        "away": away_ctx,
        "comparison": {
            "rank_gap": rank_gap, "points_gap": points_gap,
            "home_pressure": hp, "away_pressure": ap,
            "asymmetry": asymmetry,
        },
        "coverage": {
            "available": True, "status": coverage_status,
            "format_status": format_status,
            "motivation_status": coverage_status,
            "limitations": list(dict.fromkeys(limitations)),
        },
    }
