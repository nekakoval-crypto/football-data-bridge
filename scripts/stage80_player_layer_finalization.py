#!/usr/bin/env python3
"""Stage80 player-layer finalization research pipeline.

Provider-free, retrospective and fail-closed.

This stage uses already-persisted PBK history to remove the remaining *data
engineering* blockers from checklist item 10 where the evidence supports it:

* materialize historical Player Importance from official starting-XI history
  and terminal fixture results;
* join each historical XI to strictly-earlier player-match grades by fixture
  chronology, never to the target match's own grade;
* build rotation/outcome and absence/outcome research datasets;
* reconstruct return-after-recorded-injury events only as retrospective
  evidence;
* emit a final readiness gate that distinguishes "dataset exists" from
  "predictive betting authority".

Important temporal limitation:
historical lineups/injuries were retrieved after the historical fixtures.  They
are therefore RETROSPECTIVE_ONLY.  A chronological prior-match grade join avoids
outcome leakage inside the reconstructed history, but it does NOT prove that the
same evidence was actually observed before kickoff at the time.

No signal, probability, EV, canonical eligibility, stake, settlement or Forward
Journal mutation is permitted here.
"""
from __future__ import annotations

import bisect
import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any
from player_snapshot_store import read_snapshot_rows

OPS = Path(os.getenv("OPS_DIR", "ops"))

LINEUPS = OPS / "historical_lineup_snapshots.csv"
INJURIES = OPS / "historical_injury_snapshots.csv"
FIXTURES = OPS / "pbk16_all_competition_fixture_history.csv"
GRADES = OPS / "player_grade_snapshots.csv"
FORM = OPS / "player_form_walk_forward.csv"
INT_RETURN = OPS / "international_duty_player_return_load.csv"
HIST_PLAYER_META = OPS / "stage77_historical_player_backfill_last_run.json"
HIST_AVAIL_META = OPS / "stage80_historical_lineup_injury_backfill_last_run.json"

IMPORTANCE_OUT = OPS / "player_importance_research.csv"
XI_QUALITY_OUT = OPS / "player_layer_xi_quality_research.csv"
ROTATION_VALIDATION_OUT = OPS / "player_layer_rotation_validation_dataset.csv"
AVAILABILITY_VALIDATION_OUT = OPS / "player_layer_availability_validation_dataset.csv"
RETURN_OUT = OPS / "player_layer_return_reconstruction.csv"
READINESS_OUT = OPS / "player_layer_final_readiness.json"

VERSION = "PBK_STAGE80_PLAYER_LAYER_FINALIZATION_V1"

IMPORTANCE_FIELDS = [
    "team_id", "team_name", "player_id", "player_name", "position_group",
    "eligible", "status", "starts", "without_starts", "points_with",
    "points_without", "goal_diff_with", "goal_diff_without", "points_delta",
    "goal_diff_delta", "shrinkage_weight", "importance_score", "sample_reason",
    "research_only", "creates_signal", "probability_mutation",
    "eligibility_mutation", "stake_changes",
]

XI_FIELDS = [
    "fixture_id", "kickoff_utc", "team_id", "team_name", "side",
    "previous_fixture_id", "previous_kickoff_utc",
    "starting_xi_count", "previous_xi_count", "retained_starters",
    "changed_in_count", "changed_out_count", "xi_stability_pct",
    "xi_quality_prior", "previous_xi_quality_at_same_cutoff",
    "quality_delta_vs_previous_membership", "covered_players",
    "previous_covered_players", "quality_coverage_pct",
    "previous_quality_coverage_pct", "grade_history_matches_mean",
    "quality_status", "grade_basis", "temporal_authority",
    "prematch_observation_time_known", "research_only",
]

ROTATION_FIELDS = [
    "fixture_id", "kickoff_utc", "team_id", "team_name", "side",
    "changed_in_count", "changed_out_count", "retained_starters",
    "xi_stability_pct", "xi_quality_prior",
    "quality_delta_vs_previous_membership", "quality_status",
    "team_points", "team_goal_diff", "win", "draw", "loss",
    "outcome_known_after_match_only", "temporal_authority",
    "validation_authority", "research_only",
]

AVAILABILITY_FIELDS = [
    "fixture_id", "kickoff_utc", "team_id", "team_name",
    "player_id", "player_name", "availability_type", "reason",
    "player_importance_score", "importance_eligible",
    "prior_player_quality", "prior_quality_matches",
    "team_points", "team_goal_diff", "win", "draw", "loss",
    "injury_retrieved_at_utc", "temporal_authority",
    "prematch_observation_time_known", "validation_authority",
    "research_only",
]

RETURN_FIELDS = [
    "team_id", "team_name", "player_id", "player_name",
    "injury_fixture_id", "injury_kickoff_utc",
    "return_fixture_id", "return_kickoff_utc", "fixtures_between_captured",
    "return_as_starter", "prior_player_quality", "prior_quality_matches",
    "return_team_points", "return_team_goal_diff",
    "temporal_authority", "prematch_observation_time_known",
    "validation_authority", "research_only",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def sval(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def fnum(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def parse_xi(value: Any) -> list[dict[str, str]]:
    try:
        raw = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list) or len(raw) != 11:
        return []
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            return []
        player = item.get("player") if isinstance(item.get("player"), dict) else item
        pid = str(player.get("id") or player.get("player_id") or "").strip()
        name = str(player.get("name") or player.get("player_name") or "").strip()
        if not pid or pid in seen:
            return []
        seen.add(pid)
        output.append({"player_id": pid, "player_name": name})
    return output


def fixture_outcomes(fixture_rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Index terminal PBK16 fixture results by the same provider fixture ids used
    by the historical lineup/injury backfill.

    The canonical source is pbk16_all_competition_fixture_history.csv.  It uses
    status + home_goals/away_goals, whereas the newer rolling historical fixture
    catalog uses latest_status + final_score_*.  Supporting both schemas keeps
    this helper testable/fail-closed without ever joining by fuzzy team names.
    """
    out: dict[str, dict[str, Any]] = {}
    for row in fixture_rows:
        fid = sval(row, "fixture_id", "api_fixture_id")
        if not fid:
            continue
        terminal = sval(row, "terminal_observed").upper()
        status = sval(row, "status", "latest_status").upper()
        hg = fnum(
            row.get("home_goals")
            if row.get("home_goals") not in (None, "")
            else row.get("final_score_home", row.get("score_home"))
        )
        ag = fnum(
            row.get("away_goals")
            if row.get("away_goals") not in (None, "")
            else row.get("final_score_away", row.get("score_away"))
        )
        if hg is None or ag is None:
            continue
        if terminal not in {"YES", "TRUE", "1"} and status not in {"FINISHED", "FT", "AET", "PEN"}:
            continue
        out[fid] = {
            "home_points": 3 if hg > ag else (1 if hg == ag else 0),
            "away_points": 3 if ag > hg else (1 if hg == ag else 0),
            "home_gd": hg - ag,
            "away_gd": ag - hg,
        }
    return out


def lineup_history(lineup_rows: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for row in lineup_rows:
        fid = sval(row, "fixture_id", "api_fixture_id")
        team_id = sval(row, "team_id")
        kickoff = sval(row, "kickoff_utc")
        side = sval(row, "side").upper()
        xi = parse_xi(row.get("starting_xi_json"))
        if not fid or not team_id or not kickoff or side not in {"HOME", "AWAY"} or len(xi) != 11:
            continue
        key = (fid, team_id)
        if key in seen:
            continue
        seen.add(key)
        by_team[team_id].append({
            "fixture_id": fid,
            "kickoff_utc": kickoff,
            "kickoff_dt": parse_dt(kickoff),
            "team_id": team_id,
            "team_name": sval(row, "team_name"),
            "side": side,
            "xi": xi,
        })
    for rows in by_team.values():
        rows.sort(key=lambda r: ((r["kickoff_dt"] or datetime.min.replace(tzinfo=timezone.utc)), r["fixture_id"]))
    return by_team


def grade_history(grade_rows: list[dict[str, str]]) -> tuple[
    dict[str, list[tuple[datetime, float, float, str]]],
    dict[str, str],
    dict[str, str],
]:
    by_player: dict[str, list[tuple[datetime, float, float, str]]] = defaultdict(list)
    names: dict[str, str] = {}
    positions: dict[str, str] = {}
    for row in grade_rows:
        pid = sval(row, "player_id")
        kickoff = parse_dt(row.get("kickoff_utc"))
        grade = fnum(row.get("overall_grade"))
        minutes = fnum(row.get("minutes")) or 0.0
        if not pid or kickoff is None or grade is None:
            continue
        by_player[pid].append((kickoff, grade, minutes, sval(row, "fixture_id")))
        if sval(row, "player_name"):
            names[pid] = sval(row, "player_name")
        if sval(row, "position_group"):
            positions[pid] = sval(row, "position_group")
    for rows in by_player.values():
        rows.sort(key=lambda item: (item[0], item[3]))
    return by_player, names, positions


def prior_grade(
    player_id: str,
    cutoff: datetime,
    histories: dict[str, list[tuple[datetime, float, float, str]]],
    *,
    max_matches: int = 5,
    min_minutes: float = 30.0,
) -> tuple[float | None, int]:
    rows = histories.get(player_id) or []
    if not rows:
        return None, 0
    kickoffs = [item[0] for item in rows]
    index = bisect.bisect_left(kickoffs, cutoff)
    eligible = [item for item in rows[:index] if item[2] >= min_minutes]
    sample = eligible[-max_matches:]
    if not sample:
        return None, 0
    return round(mean(item[1] for item in sample), 3), len(sample)


def membership_quality(
    xi: list[dict[str, str]],
    cutoff: datetime,
    histories: dict[str, list[tuple[datetime, float, float, str]]],
) -> dict[str, Any]:
    values: list[float] = []
    samples: list[int] = []
    for player in xi:
        value, sample = prior_grade(player["player_id"], cutoff, histories)
        if value is not None:
            values.append(value)
            samples.append(sample)
    covered = len(values)
    return {
        "quality": round(mean(values), 3) if values else None,
        "covered": covered,
        "coverage_pct": round(100.0 * covered / max(len(xi), 1), 3),
        "sample_mean": round(mean(samples), 3) if samples else 0.0,
    }


def build_importance(
    lineups_by_team: dict[str, list[dict[str, Any]]],
    outcomes: dict[str, dict[str, Any]],
    player_names: dict[str, str],
    positions: dict[str, str],
    *,
    min_with: int = 5,
    min_without: int = 5,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for team_id, rows in sorted(lineups_by_team.items()):
        matches: list[dict[str, Any]] = []
        names: dict[str, str] = {}
        for row in rows:
            result = outcomes.get(row["fixture_id"])
            if not result:
                continue
            side = row["side"].lower()
            points = result.get(f"{side}_points")
            gd = result.get(f"{side}_gd")
            starters = {p["player_id"] for p in row["xi"]}
            for p in row["xi"]:
                if p["player_name"]:
                    names[p["player_id"]] = p["player_name"]
            matches.append({
                "points": points,
                "gd": gd,
                "starters": starters,
                "team_name": row["team_name"],
            })
        all_players = sorted({pid for match in matches for pid in match["starters"]})
        for pid in all_players:
            with_rows = [m for m in matches if pid in m["starters"]]
            without_rows = [m for m in matches if pid not in m["starters"]]
            eligible = len(with_rows) >= min_with and len(without_rows) >= min_without
            p_with = mean(m["points"] for m in with_rows) if with_rows else None
            p_without = mean(m["points"] for m in without_rows) if without_rows else None
            gd_with = mean(m["gd"] for m in with_rows) if with_rows else None
            gd_without = mean(m["gd"] for m in without_rows) if without_rows else None
            points_delta = round(p_with - p_without, 3) if eligible else None
            gd_delta = round(gd_with - gd_without, 3) if eligible else None
            shrinkage = min(1.0, min(len(with_rows), len(without_rows)) / 20.0) if eligible else 0.0
            score = (
                round((points_delta * 0.7 + gd_delta * 0.3) * shrinkage, 3)
                if eligible else None
            )
            output.append({
                "team_id": team_id,
                "team_name": matches[0]["team_name"] if matches else "",
                "player_id": pid,
                "player_name": names.get(pid) or player_names.get(pid) or "",
                "position_group": positions.get(pid) or "",
                "eligible": "true" if eligible else "false",
                "status": "RESEARCH_ESTIMATE" if eligible else "UNKNOWN",
                "starts": len(with_rows),
                "without_starts": len(without_rows),
                "points_with": round(p_with, 3) if p_with is not None else "",
                "points_without": round(p_without, 3) if p_without is not None else "",
                "goal_diff_with": round(gd_with, 3) if gd_with is not None else "",
                "goal_diff_without": round(gd_without, 3) if gd_without is not None else "",
                "points_delta": points_delta if points_delta is not None else "",
                "goal_diff_delta": gd_delta if gd_delta is not None else "",
                "shrinkage_weight": round(shrinkage, 3),
                "importance_score": score if score is not None else "",
                "sample_reason": (
                    "OK"
                    if eligible
                    else f"INSUFFICIENT_CAPTURED_SAMPLE_WITH_{len(with_rows)}_WITHOUT_{len(without_rows)}"
                ),
                "research_only": "true",
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
            })
    return output


def build_xi_quality(
    lineups_by_team: dict[str, list[dict[str, Any]]],
    histories: dict[str, list[tuple[datetime, float, float, str]]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for team_id, rows in sorted(lineups_by_team.items()):
        previous = None
        for row in rows:
            cutoff = row["kickoff_dt"]
            if cutoff is None:
                previous = row
                continue
            current_q = membership_quality(row["xi"], cutoff, histories)
            if previous is None:
                previous = row
                continue
            previous_q = membership_quality(previous["xi"], cutoff, histories)
            current_ids = {p["player_id"] for p in row["xi"]}
            previous_ids = {p["player_id"] for p in previous["xi"]}
            retained = len(current_ids & previous_ids)
            changed_in = len(current_ids - previous_ids)
            changed_out = len(previous_ids - current_ids)
            delta = None
            if (
                current_q["quality"] is not None
                and previous_q["quality"] is not None
                and current_q["covered"] >= 8
                and previous_q["covered"] >= 8
            ):
                delta = round(current_q["quality"] - previous_q["quality"], 3)
            output.append({
                "fixture_id": row["fixture_id"],
                "kickoff_utc": row["kickoff_utc"],
                "team_id": team_id,
                "team_name": row["team_name"],
                "side": row["side"],
                "previous_fixture_id": previous["fixture_id"],
                "previous_kickoff_utc": previous["kickoff_utc"],
                "starting_xi_count": 11,
                "previous_xi_count": 11,
                "retained_starters": retained,
                "changed_in_count": changed_in,
                "changed_out_count": changed_out,
                "xi_stability_pct": round(100.0 * retained / 11.0, 3),
                "xi_quality_prior": current_q["quality"] if current_q["quality"] is not None else "",
                "previous_xi_quality_at_same_cutoff": previous_q["quality"] if previous_q["quality"] is not None else "",
                "quality_delta_vs_previous_membership": delta if delta is not None else "",
                "covered_players": current_q["covered"],
                "previous_covered_players": previous_q["covered"],
                "quality_coverage_pct": current_q["coverage_pct"],
                "previous_quality_coverage_pct": previous_q["coverage_pct"],
                "grade_history_matches_mean": current_q["sample_mean"],
                "quality_status": "RESEARCH_COMPONENT" if delta is not None else "DATA_BLOCKED",
                "grade_basis": "STRICTLY_PRIOR_MATCH_CHRONOLOGY_FORM5_MIN30",
                "temporal_authority": "RETROSPECTIVE_CHRONOLOGY_ONLY",
                "prematch_observation_time_known": "NO",
                "research_only": "YES",
            })
            previous = row
    return output


def outcome_columns(result: dict[str, Any], side: str) -> dict[str, Any]:
    points = result.get(f"{side.lower()}_points")
    gd = result.get(f"{side.lower()}_gd")
    return {
        "team_points": points,
        "team_goal_diff": gd,
        "win": "YES" if points == 3 else "NO",
        "draw": "YES" if points == 1 else "NO",
        "loss": "YES" if points == 0 else "NO",
    }


def build_rotation_validation(
    xi_rows: list[dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    for row in xi_rows:
        result = outcomes.get(str(row["fixture_id"]))
        if not result:
            continue
        payload = {key: row.get(key, "") for key in XI_FIELDS}
        outcome = outcome_columns(result, str(row["side"]))
        output.append({
            "fixture_id": row["fixture_id"],
            "kickoff_utc": row["kickoff_utc"],
            "team_id": row["team_id"],
            "team_name": row["team_name"],
            "side": row["side"],
            "changed_in_count": row["changed_in_count"],
            "changed_out_count": row["changed_out_count"],
            "retained_starters": row["retained_starters"],
            "xi_stability_pct": row["xi_stability_pct"],
            "xi_quality_prior": row["xi_quality_prior"],
            "quality_delta_vs_previous_membership": row["quality_delta_vs_previous_membership"],
            "quality_status": row["quality_status"],
            **outcome,
            "outcome_known_after_match_only": "YES",
            "temporal_authority": "RETROSPECTIVE_CHRONOLOGY_ONLY",
            "validation_authority": "ASSOCIATION_DATASET_ONLY",
            "research_only": "YES",
        })
    return output


def importance_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(row.get("team_id") or ""), str(row.get("player_id") or "")): row
        for row in rows
        if row.get("team_id") and row.get("player_id")
    }


def build_availability_validation(
    injury_rows: list[dict[str, str]],
    outcomes: dict[str, dict[str, Any]],
    importance_rows: list[dict[str, Any]],
    histories: dict[str, list[tuple[datetime, float, float, str]]],
) -> list[dict[str, Any]]:
    imp = importance_index(importance_rows)
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in injury_rows:
        fid = sval(row, "fixture_id", "api_fixture_id")
        team_id = sval(row, "team_id")
        player_id = sval(row, "player_id")
        side = ""
        if not fid or not team_id or not player_id:
            continue
        result = outcomes.get(fid)
        if not result:
            continue
        # infer side from score-bearing lineup history is intentionally avoided;
        # use home/away names in the injury row only when exact team-name identity matches.
        team_name = sval(row, "team_name")
        home_name = sval(row, "home_team")
        away_name = sval(row, "away_team")
        if team_name and team_name == home_name:
            side = "HOME"
        elif team_name and team_name == away_name:
            side = "AWAY"
        if not side:
            continue
        kickoff = parse_dt(row.get("kickoff_utc"))
        if kickoff is None:
            continue
        key = (fid, team_id, player_id, sval(row, "reason"))
        if key in seen:
            continue
        seen.add(key)
        prior_quality, prior_matches = prior_grade(player_id, kickoff, histories)
        importance = imp.get((team_id, player_id)) or {}
        outcome = outcome_columns(result, side)
        output.append({
            "fixture_id": fid,
            "kickoff_utc": sval(row, "kickoff_utc"),
            "team_id": team_id,
            "team_name": team_name,
            "player_id": player_id,
            "player_name": sval(row, "player_name"),
            "availability_type": sval(row, "availability_type"),
            "reason": sval(row, "reason"),
            "player_importance_score": importance.get("importance_score", ""),
            "importance_eligible": importance.get("eligible", "false"),
            "prior_player_quality": prior_quality if prior_quality is not None else "",
            "prior_quality_matches": prior_matches,
            **outcome,
            "injury_retrieved_at_utc": sval(row, "retrieved_at_utc"),
            "temporal_authority": "RETROSPECTIVE_ONLY",
            "prematch_observation_time_known": "NO",
            "validation_authority": "DESCRIPTIVE_ASSOCIATION_ONLY",
            "research_only": "YES",
        })
    return output


def build_return_reconstruction(
    lineups_by_team: dict[str, list[dict[str, Any]]],
    injury_rows: list[dict[str, str]],
    outcomes: dict[str, dict[str, Any]],
    histories: dict[str, list[tuple[datetime, float, float, str]]],
) -> list[dict[str, Any]]:
    injury_by_team_player: dict[tuple[str, str], list[tuple[datetime, str, str, str]]] = defaultdict(list)
    names: dict[tuple[str, str], str] = {}
    for row in injury_rows:
        team_id = sval(row, "team_id")
        player_id = sval(row, "player_id")
        kickoff = parse_dt(row.get("kickoff_utc"))
        fid = sval(row, "fixture_id", "api_fixture_id")
        if not team_id or not player_id or kickoff is None or not fid:
            continue
        injury_by_team_player[(team_id, player_id)].append(
            (kickoff, fid, sval(row, "kickoff_utc"), sval(row, "player_name"))
        )
        names[(team_id, player_id)] = sval(row, "player_name")
    for values in injury_by_team_player.values():
        values.sort()

    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for team_id, rows in lineups_by_team.items():
        for index, row in enumerate(rows):
            starters = {p["player_id"] for p in row["xi"]}
            for player_id in starters:
                injuries = injury_by_team_player.get((team_id, player_id)) or []
                prior = [item for item in injuries if item[0] < row["kickoff_dt"]]
                if not prior:
                    continue
                injury = prior[-1]
                # If any captured lineup between injury and return already contains the
                # player, this is not the first observed return in our captured history.
                between = [
                    earlier for earlier in rows
                    if injury[0] < earlier["kickoff_dt"] < row["kickoff_dt"]
                ]
                if any(player_id in {p["player_id"] for p in earlier["xi"]} for earlier in between):
                    continue
                key = (team_id, player_id, row["fixture_id"])
                if key in seen:
                    continue
                seen.add(key)
                prior_quality, prior_matches = prior_grade(player_id, row["kickoff_dt"], histories)
                result = outcomes.get(row["fixture_id"])
                outcome = outcome_columns(result, row["side"]) if result else {
                    "team_points": "", "team_goal_diff": ""
                }
                output.append({
                    "team_id": team_id,
                    "team_name": row["team_name"],
                    "player_id": player_id,
                    "player_name": names.get((team_id, player_id)) or "",
                    "injury_fixture_id": injury[1],
                    "injury_kickoff_utc": injury[2],
                    "return_fixture_id": row["fixture_id"],
                    "return_kickoff_utc": row["kickoff_utc"],
                    "fixtures_between_captured": len(between),
                    "return_as_starter": "YES",
                    "prior_player_quality": prior_quality if prior_quality is not None else "",
                    "prior_quality_matches": prior_matches,
                    "return_team_points": outcome.get("team_points", ""),
                    "return_team_goal_diff": outcome.get("team_goal_diff", ""),
                    "temporal_authority": "RETROSPECTIVE_ONLY",
                    "prematch_observation_time_known": "NO",
                    "validation_authority": "RETURN_RECONSTRUCTION_ONLY",
                    "research_only": "YES",
                })
    return output


def component(status: str, evidence: dict[str, Any], blockers: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "authority": "RESEARCH",
        "evidence": evidence,
        "blockers": blockers or [],
    }


def build_readiness(
    *,
    importance_rows: list[dict[str, Any]],
    xi_rows: list[dict[str, Any]],
    rotation_rows: list[dict[str, Any]],
    availability_rows: list[dict[str, Any]],
    return_rows: list[dict[str, Any]],
    form_rows: list[dict[str, str]],
    international_rows: list[dict[str, str]],
    player_meta: dict[str, Any],
    availability_meta: dict[str, Any],
) -> dict[str, Any]:
    eligible_importance = sum(str(r.get("eligible")).lower() == "true" for r in importance_rows)
    xi_quality_ready = sum(r.get("quality_status") == "RESEARCH_COMPONENT" for r in xi_rows)
    player_remaining = int(player_meta.get("remaining_unattempted_or_retryable") or 0)
    availability_remaining = int(availability_meta.get("remaining_candidate_tasks") or 0)

    components = {
        "PLAYER_QUALITY": component(
            "VALIDATION_PENDING" if xi_quality_ready else "RESEARCH_ONLY",
            {
                "strictly_prior_xi_quality_rows": len(xi_rows),
                "xi_quality_rows_with_8plus_coverage": xi_quality_ready,
                "historical_player_remaining": player_remaining,
                "basis": "STRICTLY_PRIOR_MATCH_CHRONOLOGY_FORM5_MIN30",
                "temporal_authority": "RETROSPECTIVE_CHRONOLOGY_ONLY",
            },
            [] if xi_quality_ready else ["INSUFFICIENT_STRICTLY_PRIOR_GRADE_COVERAGE"],
        ),
        "CURRENT_FORM": component(
            "VALIDATION_PENDING" if form_rows else "DATA_MISSING",
            {"walk_forward_rows": len(form_rows)},
            [] if form_rows else ["NO_PLAYER_FORM_ROWS"],
        ),
        "PLAYER_IMPORTANCE": component(
            "VALIDATION_PENDING" if eligible_importance else "RESEARCH_ONLY",
            {
                "importance_rows": len(importance_rows),
                "eligible_importance_rows": eligible_importance,
                "minimum_with_starts": 5,
                "minimum_without_starts": 5,
                "causal_claim": False,
            },
            [] if eligible_importance else ["NO_PLAYER_HAS_SUFFICIENT_WITH_WITHOUT_CAPTURED_SAMPLE"],
        ),
        "AVAILABILITY_ABSENCE": component(
            "RESEARCH_ONLY",
            {
                "descriptive_association_rows": len(availability_rows),
                "historical_availability_remaining_tasks": availability_remaining,
                "prematch_observation_time_known": False,
            },
            [
                "RETROSPECTIVE_INJURY_EVIDENCE_CANNOT_PROVE_PREMATCH_KNOWLEDGE",
                "GENUINE_PREMATCH_ABSENCE_EVIDENCE_REQUIRED_FOR_PREDICTIVE_VALIDATION",
            ],
        ),
        "RETURN_IMPACT": component(
            "RESEARCH_ONLY",
            {
                "retrospective_return_reconstructions": len(return_rows),
                "prematch_observation_time_known": False,
            },
            [
                "RETURN_RECONSTRUCTION_IS_RETROSPECTIVE",
                "GENUINE_PREMATCH_RETURN_EVIDENCE_REQUIRED_FOR_PREDICTIVE_VALIDATION",
            ],
        ),
        "XI_ROTATION": component(
            "VALIDATION_PENDING" if rotation_rows and xi_quality_ready else "RESEARCH_ONLY",
            {
                "rotation_outcome_rows": len(rotation_rows),
                "strictly_prior_quality_rows": xi_quality_ready,
                "market_adjusted_validation_completed": False,
            },
            [
                "MARKET_ADJUSTED_OUT_OF_SAMPLE_VALIDATION_NOT_COMPLETED",
                "RETROSPECTIVE_LINEUP_OBSERVATION_TIME_NOT_KNOWN",
            ],
        ),
        "INTERNATIONAL_RETURN_LOAD": component(
            "VALIDATION_PENDING" if international_rows else "DATA_MISSING",
            {"return_load_rows": len(international_rows)},
            [] if international_rows else ["NO_INTERNATIONAL_RETURN_LOAD_ROWS"],
        ),
        "DOUBLE_COUNTING_GOVERNANCE": {
            "status": "OPERATIONAL_AUTHORIZED",
            "authority": "GOVERNANCE",
            "evidence": {
                "raw_additive_mega_score_forbidden": True,
                "player_quality_distinct_from_current_form": True,
                "availability_distinct_from_rotation": True,
                "international_load_distinct_from_club_form": True,
                "specialist_model_required": True,
            },
            "blockers": [],
        },
    }

    predictive_statuses = [
        components[key]["status"]
        for key in (
            "PLAYER_QUALITY",
            "CURRENT_FORM",
            "PLAYER_IMPORTANCE",
            "AVAILABILITY_ABSENCE",
            "RETURN_IMPACT",
            "XI_ROTATION",
            "INTERNATIONAL_RETURN_LOAD",
        )
    ]
    overall = "VALIDATION_PENDING" if any(s == "VALIDATION_PENDING" for s in predictive_statuses) else "RESEARCH_ONLY"

    hard_blockers = [
        "GENUINE_PREMATCH_AVAILABILITY_TIMESTAMPS_NOT_AVAILABLE_FOR_HISTORICAL_BACKFILL",
        "MARKET_ADJUSTED_OUT_OF_SAMPLE_PLAYER_LAYER_VALIDATION_NOT_COMPLETE",
    ]
    if player_remaining > 0:
        hard_blockers.append("HISTORICAL_PLAYER_BACKFILL_INCOMPLETE")
    if availability_remaining > 0:
        hard_blockers.append("HISTORICAL_LINEUP_INJURY_BACKFILL_INCOMPLETE")

    return {
        "version": VERSION,
        "run_at_utc": utc_now(),
        "status": overall,
        "checklist_item_10_data_engineering_foundation": "COMPLETE",
        "checklist_item_10_predictive_authority": "NOT_AUTHORIZED",
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "components": components,
        "hard_blockers": hard_blockers,
        "closure_rule": (
            "Checklist item 10 may be considered DATA/RESEARCH FOUNDATION COMPLETE, "
            "but must not be called OPERATIONAL PREDICTIVE COMPLETE until genuine "
            "prematch availability evidence and market-adjusted OOS validation pass."
        ),
    }


def main() -> None:
    lineup_rows = read_csv(LINEUPS)
    injury_rows = read_csv(INJURIES)
    fixture_rows = read_csv(FIXTURES)
    grade_rows = read_snapshot_rows(GRADES)
    form_rows = read_csv(FORM)
    international_rows = read_csv(INT_RETURN)
    player_meta = read_json(HIST_PLAYER_META)
    availability_meta = read_json(HIST_AVAIL_META)

    outcomes = fixture_outcomes(fixture_rows)
    lineups = lineup_history(lineup_rows)
    histories, player_names, positions = grade_history(grade_rows)

    importance = build_importance(lineups, outcomes, player_names, positions)
    xi_quality = build_xi_quality(lineups, histories)
    rotation_validation = build_rotation_validation(xi_quality, outcomes)
    availability_validation = build_availability_validation(
        injury_rows, outcomes, importance, histories
    )
    returns = build_return_reconstruction(lineups, injury_rows, outcomes, histories)

    write_csv(IMPORTANCE_OUT, IMPORTANCE_FIELDS, importance)
    write_csv(XI_QUALITY_OUT, XI_FIELDS, xi_quality)
    write_csv(ROTATION_VALIDATION_OUT, ROTATION_FIELDS, rotation_validation)
    write_csv(AVAILABILITY_VALIDATION_OUT, AVAILABILITY_FIELDS, availability_validation)
    write_csv(RETURN_OUT, RETURN_FIELDS, returns)

    readiness = build_readiness(
        importance_rows=importance,
        xi_rows=xi_quality,
        rotation_rows=rotation_validation,
        availability_rows=availability_validation,
        return_rows=returns,
        form_rows=form_rows,
        international_rows=international_rows,
        player_meta=player_meta,
        availability_meta=availability_meta,
    )
    write_json(READINESS_OUT, readiness)
    print(json.dumps(readiness, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
