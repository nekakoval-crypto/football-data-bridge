#!/usr/bin/env python3
"""Manual lineup WHAT-IF scenarios for PBK.

A scenario is user-supplied research context. It never overwrites provider
lineups or mutates canonical probability, Forward eligibility, stakes or
settlement. It may be saved as append-only JSONL evidence for later research.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from player_grade import xi_quality

SCENARIO_VERSION = "PBK_MANUAL_LINEUP_SCENARIO_V1"


def _iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _player_id(player):
    return str((player or {}).get("id") or (player or {}).get("player_id") or "").strip()


def _clean_xi(xi):
    output = []
    for raw in xi or []:
        player = dict(raw or {})
        pid = _player_id(player)
        if not pid:
            continue
        output.append({
            "id": pid,
            "name": player.get("name") or player.get("player_name"),
            "lastname": player.get("lastname") or player.get("last_name"),
            "number": player.get("number"),
            "pos": player.get("pos") or player.get("position"),
            "grid": player.get("grid"),
        })
    return output


def validate_side(side, allow_draft=False):
    formation = str((side or {}).get("formation") or "").strip() or None
    xi = _clean_xi((side or {}).get("xi") or (side or {}).get("starting_xi"))
    ids = [_player_id(p) for p in xi]
    errors = []
    if len(ids) != len(set(ids)):
        errors.append("DUPLICATE_PLAYER")
    if not allow_draft and len(xi) != 11:
        errors.append("STARTING_XI_MUST_HAVE_11_PLAYERS")
    if allow_draft and len(xi) > 11:
        errors.append("DRAFT_XI_CANNOT_EXCEED_11_PLAYERS")
    if not formation:
        errors.append("FORMATION_REQUIRED")
    return {"valid": not errors, "errors": errors, "formation": formation, "xi": xi}


def _display_line(player):
    text = str(player.get("pos") or "").upper()
    if text.startswith("G"):
        return "GK"
    if text.startswith("D"):
        return "DEF"
    if text.startswith("F") or text in {"ST", "CF", "LW", "RW"}:
        return "ATT"
    return "MID"


def compare_xi(baseline_xi, manual_xi, grades_by_player=None):
    baseline = _clean_xi(baseline_xi)
    manual = _clean_xi(manual_xi)
    base_ids = {_player_id(p): p for p in baseline}
    man_ids = {_player_id(p): p for p in manual}
    removed = [base_ids[pid] for pid in base_ids.keys() - man_ids.keys()]
    added = [man_ids[pid] for pid in man_ids.keys() - base_ids.keys()]
    baseline_quality = xi_quality(baseline, grades_by_player or {})
    manual_quality = xi_quality(manual, grades_by_player or {})
    q0, q1 = baseline_quality.get("xi_quality"), manual_quality.get("xi_quality")
    quality_delta = round(q1 - q0, 2) if q0 is not None and q1 is not None else None

    lines = {}
    for label, players in (("baseline", baseline), ("manual", manual)):
        for player in players:
            pid = _player_id(player)
            grade = (grades_by_player or {}).get(pid)
            value = grade.get("overall_grade") if isinstance(grade, dict) else grade
            if value is None:
                continue
            line = _display_line(player)
            lines.setdefault(line, {"baseline": [], "manual": []})[label].append(float(value))
    line_delta = {}
    for line, values in lines.items():
        if values["baseline"] and values["manual"]:
            b = sum(values["baseline"]) / len(values["baseline"])
            m = sum(values["manual"]) / len(values["manual"])
            line_delta[line] = round(m - b, 2)
        else:
            line_delta[line] = None
    return {
        "removed": removed,
        "added": added,
        "overlap": len(set(base_ids) & set(man_ids)),
        "baseline_quality": baseline_quality,
        "manual_quality": manual_quality,
        "xi_quality_delta": quality_delta,
        "line_quality_delta": line_delta,
    }


def _baseline_team(lineup_context, side):
    team = (lineup_context or {}).get(side) or {}
    official = team.get("official") or {}
    expected = team.get("expected") or {}
    if official.get("xi"):
        return {"status": "OFFICIAL", "formation": official.get("formation"), "xi": official.get("xi"), "source": official.get("source")}
    if expected.get("xi"):
        return {"status": "EXPECTED", "formation": expected.get("formation"), "xi": expected.get("xi"), "source": expected.get("source")}
    return {"status": "UNKNOWN", "formation": team.get("formation"), "xi": team.get("starting_xi") or [], "source": None}


def build_scenario(fixture_id, lineup_context, manual, grades_by_player=None,
                   importance_by_player=None, source_note=None, scenario_name=None,
                   created_at_utc=None, allow_draft=False):
    """Build one manual scenario against the best current provider baseline."""
    fixture_id = str(fixture_id or "").strip()
    created_at_utc = created_at_utc or _iso_now()
    if not fixture_id:
        raise ValueError("fixture_id is required")
    sides = {}
    errors = []
    for side in ("home", "away"):
        validated = validate_side((manual or {}).get(side) or {}, allow_draft=allow_draft)
        if not validated["valid"]:
            errors.extend(f"{side.upper()}:{item}" for item in validated["errors"])
        baseline = _baseline_team(lineup_context, side)
        comparison = compare_xi(baseline.get("xi"), validated["xi"], grades_by_player)
        importance_delta = None
        if importance_by_player:
            removed_imp = sum(float(importance_by_player.get(_player_id(p), 0) or 0) for p in comparison["removed"])
            added_imp = sum(float(importance_by_player.get(_player_id(p), 0) or 0) for p in comparison["added"])
            importance_delta = round(added_imp - removed_imp, 3)
        sides[side] = {
            "manual": {"formation": validated["formation"], "xi": validated["xi"]},
            "baseline": baseline,
            "formation_changed": bool(validated["formation"] and baseline.get("formation") and validated["formation"] != baseline.get("formation")),
            "comparison": comparison,
            "importance_delta": importance_delta,
        }

    draft = bool(allow_draft and any(len(sides[s]["manual"]["xi"]) != 11 for s in sides))
    status = "INVALID" if errors else ("DRAFT" if draft else "READY")
    payload = {
        "version": SCENARIO_VERSION,
        "fixture_id": fixture_id,
        "scenario_name": scenario_name or "Manual lineup scenario",
        "created_at_utc": created_at_utc,
        "source_label": "MANUAL/INSIDER",
        "source_note": source_note,
        "status": status,
        "errors": errors,
        "home": sides["home"],
        "away": sides["away"],
        "formation_matchup": [sides["home"]["manual"]["formation"], sides["away"]["manual"]["formation"]],
        "baseline_formation_matchup": [sides["home"]["baseline"].get("formation"), sides["away"]["baseline"].get("formation")],
        "what_if_only": True,
        "research_only": True,
        "provider_data_overwrite": False,
        "provider_polling": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "settlement_mutation": False,
        "motivation_mutation": False,
        "context_mutation": False,
    }
    fingerprint_basis = {k: v for k, v in payload.items() if k != "scenario_id"}
    payload["scenario_id"] = hashlib.sha256(_encode(fingerprint_basis).encode("utf-8")).hexdigest()
    return payload


def save_scenario(path, scenario):
    """Append a scenario once. Existing scenario bytes are never rewritten."""
    if scenario.get("status") == "INVALID":
        raise ValueError("invalid scenarios cannot be saved")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    sid = scenario.get("scenario_id")
    if any(item.get("scenario_id") == sid for item in existing):
        return False
    with path.open("a", encoding="utf-8") as stream:
        stream.write(_encode(scenario) + "\n")
    return True


def load_scenarios(path, fixture_id=None):
    path = Path(path)
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if fixture_id is not None:
        rows = [row for row in rows if str(row.get("fixture_id")) == str(fixture_id)]
    return rows
