#!/usr/bin/env python3
"""PBK Point14C — real Expected XI candidate-pool builder.

Provider-free projection over already persisted PBK evidence.

Sources:
- team_roster_history.csv
- lineup_snapshots.csv
- historical_lineup_snapshots.csv when present
- player_grade_snapshots.csv / partitioned snapshot store
- player_availability_prematch_events.csv
- player_discipline_prematch_events.csv when present

No probability, EV, R1/R2/R3, stake or Forward mutation.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

try:
    from player_snapshot_store import read_snapshot_rows
except ImportError:
    from scripts.player_snapshot_store import read_snapshot_rows


OPS = Path("ops")

ROSTERS = OPS / "team_roster_history.csv"
LINEUPS = OPS / "lineup_snapshots.csv"
HIST_LINEUPS = OPS / "historical_lineup_snapshots.csv"
GRADES = OPS / "player_grade_snapshots.csv"
AVAILABILITY = OPS / "player_availability_prematch_events.csv"
DISCIPLINE = OPS / "player_discipline_prematch_events.csv"


def _s(value: Any) -> str:
    return str(value or "").strip()


def _u(value: Any) -> str:
    return _s(value).upper()


def _dt(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(
            _s(value).replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(timezone.utc)


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        return list(csv.DictReader(stream))


def parse_xi(value: Any) -> list[dict[str, Any]]:
    try:
        raw = (
            json.loads(value)
            if isinstance(value, str)
            else value
        )
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return []

    if not isinstance(raw, list):
        return []

    out = []

    for item in raw:

        if not isinstance(item, dict):
            continue

        player = (
            item.get("player")
            if isinstance(item.get("player"), dict)
            else item
        )

        pid = _s(
            player.get("id")
            or player.get("player_id")
        )

        if not pid:
            continue

        out.append({
            "player_id": pid,

            "player_name": _s(
                player.get("name")
                or player.get("player_name")
            ),

            "provider_position": _u(
                player.get("pos")
                or player.get("position")
            ),

            "grid": _s(
                player.get("grid")
            ),
        })

    return out


def latest_roster_for_team(
    roster_rows: list[dict[str, str]],
    *,
    team_id: str,
    before_utc: str,
) -> list[dict[str, str]]:

    cutoff = _dt(before_utc)

    eligible = []

    for row in roster_rows:

        if _s(row.get("team_id")) != _s(team_id):
            continue

        captured = _dt(
            row.get("captured_at_utc")
        )

        if (
            cutoff is None
            or captured is None
            or captured > cutoff
        ):
            continue

        eligible.append(row)

    if not eligible:
        return []

    latest_stamp = max(
        _s(row.get("captured_at_utc"))
        for row in eligible
    )

    return [
        row
        for row in eligible
        if _s(row.get("captured_at_utc"))
        == latest_stamp
    ]


def broad_roster_position(value: Any) -> str:

    pos = _u(value)

    if pos.startswith("GOAL") or pos == "G":
        return "GK"

    if pos.startswith("DEF") or pos == "D":
        return "D"

    if pos.startswith("MID") or pos == "M":
        return "M"

    if (
        pos.startswith("ATT")
        or pos.startswith("FOR")
        or pos == "F"
    ):
        return "F"

    return ""


def grid_tuple(
    value: Any,
) -> tuple[int, int] | None:

    text = _s(value)

    if ":" not in text:
        return None

    left, right = text.split(":", 1)

    try:
        return int(left), int(right)

    except ValueError:
        return None


def documented_slot_from_grid(
    formation: str,
    grid: str,
) -> str:
    """Conservative exact-slot extraction."""

    parsed = grid_tuple(grid)

    if parsed is None:
        return ""

    row, col = parsed
    formation = _s(formation)

    if row == 1:
        return "GK"

    if formation == "4-3-3":

        maps = {
            2: {
                4: "RB",
                3: "CB",
                2: "CB",
                1: "LB",
            },

            3: {
                3: "CM",
                2: "CM",
                1: "CM",
            },

            4: {
                3: "RW",
                2: "ST",
                1: "LW",
            },
        }

        return maps.get(
            row,
            {},
        ).get(
            col,
            "",
        )

    if formation == "4-2-3-1":

        maps = {
            2: {
                4: "RB",
                3: "CB",
                2: "CB",
                1: "LB",
            },

            3: {
                2: "DM",
                1: "DM",
            },

            4: {
                3: "RW",
                2: "AM",
                1: "LW",
            },

            5: {
                1: "ST",
            },
        }

        return maps.get(
            row,
            {},
        ).get(
            col,
            "",
        )

    if formation == "4-4-2":

        maps = {
            2: {
                4: "RB",
                3: "CB",
                2: "CB",
                1: "LB",
            },

            3: {
                4: "RM",
                3: "CM",
                2: "CM",
                1: "LM",
            },

            4: {
                2: "ST",
                1: "ST",
            },
        }

        return maps.get(
            row,
            {},
        ).get(
            col,
            "",
        )

    if formation == "3-4-3":

        maps = {
            2: {
                3: "CB",
                2: "CB",
                1: "CB",
            },

            3: {
                4: "RWB",
                3: "CM",
                2: "CM",
                1: "LWB",
            },

            4: {
                3: "RW",
                2: "ST",
                1: "LW",
            },
        }

        return maps.get(
            row,
            {},
        ).get(
            col,
            "",
        )

    if formation == "3-5-2":

        maps = {
            2: {
                3: "CB",
                2: "CB",
                1: "CB",
            },

            3: {
                5: "RWB",
                4: "CM",
                3: "DM",
                2: "CM",
                1: "LWB",
            },

            4: {
                2: "ST",
                1: "ST",
            },
        }

        return maps.get(
            row,
            {},
        ).get(
            col,
            "",
        )

    if formation == "5-3-2":

        maps = {
            2: {
                5: "RWB",
                4: "CB",
                3: "CB",
                2: "CB",
                1: "LWB",
            },

            3: {
                3: "CM",
                2: "CM",
                1: "CM",
            },

            4: {
                2: "ST",
                1: "ST",
            },
        }

        return maps.get(
            row,
            {},
        ).get(
            col,
            "",
        )

    return ""


def prior_team_lineups(
    lineup_rows: list[dict[str, str]],
    *,
    team_id: str,
    before_utc: str,
) -> list[dict[str, Any]]:

    cutoff = _dt(before_utc)

    best: dict[str, dict[str, str]] = {}

    for row in lineup_rows:

        if _s(row.get("team_id")) != _s(team_id):
            continue

        kickoff = _dt(
            row.get("kickoff_utc")
        )

        if (
            cutoff is None
            or kickoff is None
            or kickoff >= cutoff
        ):
            continue

        fixture_id = _s(
            row.get("fixture_id")
        )

        if not fixture_id:
            continue

        current = best.get(
            fixture_id
        )

        if (
            current is None
            or _s(row.get("captured_at_utc"))
            > _s(current.get("captured_at_utc"))
        ):
            best[fixture_id] = row

    rows = list(
        best.values()
    )

    rows.sort(
        key=lambda row: (
            _s(row.get("kickoff_utc")),
            _s(row.get("fixture_id")),
        ),
        reverse=True,
    )

    output = []

    for row in rows:

        output.append({
            "fixture_id": _s(
                row.get("fixture_id")
            ),

            "kickoff_utc": _s(
                row.get("kickoff_utc")
            ),

            "formation": _s(
                row.get("formation")
            ),

            "xi": parse_xi(
                row.get("starting_xi_json")
            ),
        })

    return output


def player_usage_from_lineups(
    lineups: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:

    output: dict[
        str,
        dict[str, Any],
    ] = {}

    recent5 = lineups[:5]
    recent10 = lineups[:10]

    player_ids = {
        player["player_id"]
        for row in lineups
        for player in row["xi"]
    }

    for pid in player_ids:

        documented = []

        for row in lineups:

            formation = row["formation"]

            for player in row["xi"]:

                if player["player_id"] != pid:
                    continue

                slot = documented_slot_from_grid(
                    formation,
                    player.get("grid"),
                )

                if (
                    slot
                    and slot not in documented
                ):
                    documented.append(slot)

        output[pid] = {

            "starts_last_5": sum(
                any(
                    player["player_id"] == pid
                    for player in row["xi"]
                )
                for row in recent5
            ),

            "starts_last_10": sum(
                any(
                    player["player_id"] == pid
                    for player in row["xi"]
                )
                for row in recent10
            ),

            "documented_positions": (
                documented
            ),
        }

    return output


def grade_features(
    grade_rows: list[dict[str, str]],
    *,
    team_id: str,
    before_utc: str,
) -> dict[str, dict[str, Any]]:

    cutoff = _dt(before_utc)

    grouped = defaultdict(list)

    for row in grade_rows:

        if _s(row.get("team_id")) != _s(team_id):
            continue

        kickoff = _dt(
            row.get("kickoff_utc")
        )

        if (
            cutoff is None
            or kickoff is None
            or kickoff >= cutoff
        ):
            continue

        pid = _s(
            row.get("player_id")
        )

        if pid:
            grouped[pid].append(row)

    result = {}

    for pid, rows in grouped.items():

        rows.sort(
            key=lambda row: _s(
                row.get("kickoff_utc")
            ),
            reverse=True,
        )

        def avg_grade(n):

            values = [
                _num(
                    row.get("overall_grade")
                )
                for row in rows[:n]
            ]

            values = [
                value
                for value in values
                if value is not None
            ]

            return (
                round(
                    mean(values),
                    4,
                )
                if values
                else None
            )

        minutes = [
            _num(
                row.get("minutes")
            )
            for row in rows[:5]
        ]

        result[pid] = {

            "form_3": avg_grade(3),

            "form_5": avg_grade(5),

            "minutes_last_5": round(
                sum(
                    value
                    for value in minutes
                    if value is not None
                ),
                1,
            ),
        }

    return result


def journal_event_to_availability(
    row: dict[str, str],
) -> dict[str, Any] | None:

    pid = _s(
        row.get("player_id")
    )

    if not pid:
        return None

    state = _u(
        row.get("state")
    )

    availability_type = _u(
        row.get("availability_type")
    )

    if state == "PRESENT":

        event_type = "AVAILABILITY"
        status = "PRESENT"

    elif state == "ABSENT":

        event_type = "INJURY"

        if availability_type == "QUESTIONABLE":
            status = "QUESTIONABLE"

        else:
            status = "CONFIRMED_INJURY_OUT"

    else:
        return None

    return {
        "player_id": pid,

        "team_id": _s(
            row.get("team_id")
        ),

        "event_type": event_type,

        "status": status,

        "competition_scope": "",

        "observed_at_utc": _s(
            row.get("observed_at_utc")
        ),

        "source": _s(
            row.get("source")
        ),

        "source_reason": _s(
            row.get("reason")
        ),

        "source_availability_type": _s(
            row.get("availability_type")
        ),
    }


def availability_events_by_player(
    availability_rows: list[dict[str, str]],
    discipline_rows: list[dict[str, str]],
    *,
    team_id: str,
    before_utc: str,
) -> dict[str, list[dict[str, Any]]]:

    cutoff = _dt(before_utc)

    grouped = defaultdict(list)

    for row in availability_rows:

        if _s(row.get("team_id")) != _s(team_id):
            continue

        observed = _dt(
            row.get("observed_at_utc")
        )

        if (
            cutoff is None
            or observed is None
            or observed > cutoff
        ):
            continue

        event = (
            journal_event_to_availability(
                row
            )
        )

        if event:
            grouped[
                event["player_id"]
            ].append(event)

    for row in discipline_rows:

        if _s(row.get("team_id")) != _s(team_id):
            continue

        observed = _dt(
            row.get("observed_at_utc")
        )

        if (
            cutoff is None
            or observed is None
            or observed > cutoff
        ):
            continue

        pid = _s(
            row.get("player_id")
        )

        if not pid:
            continue

        grouped[pid].append({

            "player_id": pid,

            "team_id": _s(
                row.get("team_id")
            ),

            "event_type": _u(
                row.get("event_type")
            ),

            "status": _u(
                row.get("status")
            ),

            "competition_scope": _s(
                row.get("competition_scope")
            ),

            "observed_at_utc": _s(
                row.get("observed_at_utc")
            ),

            "source": _s(
                row.get("source")
            ),
        })

    for events in grouped.values():

        events.sort(
            key=lambda row: _s(
                row.get("observed_at_utc")
            )
        )

    return grouped


def build_candidate_pool(
    *,
    team_id: str,
    before_utc: str,
    roster_rows: list[dict[str, str]],
    lineup_rows: list[dict[str, str]],
    grade_rows: list[dict[str, str]],
    availability_rows: list[dict[str, str]],
    discipline_rows: list[dict[str, str]],
) -> dict[str, Any]:

    roster = latest_roster_for_team(
        roster_rows,
        team_id=team_id,
        before_utc=before_utc,
    )

    if not roster:

        return {
            "version": (
                "PBK_EXPECTED_XI_"
                "CANDIDATE_POOL_V1"
            ),

            "status": (
                "NO_CURRENT_ROSTER_EVIDENCE"
            ),

            "team_id": _s(
                team_id
            ),

            "before_utc": before_utc,

            "candidate_count": 0,

            "candidates": [],

            "provider_calls": 0,

            "no_lookahead": True,

            "research_only": True,

            "operational_betting_authority": (
                False
            ),

            "probability_authority": (
                "UNCALIBRATED"
            ),
        }

    prior_lineups = prior_team_lineups(
        lineup_rows,
        team_id=team_id,
        before_utc=before_utc,
    )

    usage = player_usage_from_lineups(
        prior_lineups
    )

    grades = grade_features(
        grade_rows,
        team_id=team_id,
        before_utc=before_utc,
    )

    availability = availability_events_by_player(
        availability_rows,
        discipline_rows,
        team_id=team_id,
        before_utc=before_utc,
    )

    candidates = []

    for player in roster:

        pid = _s(
            player.get("player_id")
        )

        if not pid:
            continue

        roster_position = broad_roster_position(
            player.get("position")
        )

        usage_row = usage.get(
            pid,
            {},
        )

        grade_row = grades.get(
            pid,
            {},
        )

        documented = list(
            usage_row.get(
                "documented_positions",
                [],
            )
        )

        if (
            roster_position
            and roster_position
            not in documented
        ):
            documented.append(
                roster_position
            )

        candidates.append({

            "player_id": pid,

            "player_name": _s(
                player.get("player_name")
            ),

            "primary_position": (
                documented[0]
                if documented
                else roster_position
            ),

            "documented_positions": (
                documented
            ),

            "roster_position": (
                roster_position
            ),

            "roster_captured_at_utc": _s(
                player.get(
                    "captured_at_utc"
                )
            ),

            "starts_last_5": int(
                usage_row.get(
                    "starts_last_5",
                    0,
                )
            ),

            "starts_last_10": int(
                usage_row.get(
                    "starts_last_10",
                    0,
                )
            ),

            "minutes_last_5": (
                grade_row.get(
                    "minutes_last_5",
                    0,
                )
                or 0
            ),

            "form_3": (
                grade_row.get(
                    "form_3"
                )
            ),

            "form_5": (
                grade_row.get(
                    "form_5"
                )
            ),

            "availability_events": (
                availability.get(
                    pid,
                    [],
                )
            ),

            "research_only": True,
        })

    candidates.sort(
        key=lambda row: (
            row["player_name"],
            row["player_id"],
        )
    )

    return {
        "version": (
            "PBK_EXPECTED_XI_"
            "CANDIDATE_POOL_V1"
        ),

        "status": "OK",

        "team_id": _s(
            team_id
        ),

        "before_utc": before_utc,

        "roster_snapshot": _s(
            roster[0].get(
                "captured_at_utc"
            )
        ),

        "prior_lineup_fixtures_used": (
            len(prior_lineups)
        ),

        "candidate_count": (
            len(candidates)
        ),

        "candidates": candidates,

        "provider_calls": 0,

        "no_lookahead": True,

        "research_only": True,

        "operational_betting_authority": (
            False
        ),

        "probability_authority": (
            "UNCALIBRATED"
        ),
    }


def load_real_candidate_pool(
    *,
    team_id: str,
    before_utc: str,
) -> dict[str, Any]:

    roster_rows = read_csv(
        ROSTERS
    )

    lineup_rows = (
        read_csv(HIST_LINEUPS)
        + read_csv(LINEUPS)
    )

    grade_rows = read_snapshot_rows(
        GRADES
    )

    availability_rows = read_csv(
        AVAILABILITY
    )

    discipline_rows = read_csv(
        DISCIPLINE
    )

    return build_candidate_pool(
        team_id=team_id,
        before_utc=before_utc,
        roster_rows=roster_rows,
        lineup_rows=lineup_rows,
        grade_rows=grade_rows,
        availability_rows=availability_rows,
        discipline_rows=discipline_rows,
    )
