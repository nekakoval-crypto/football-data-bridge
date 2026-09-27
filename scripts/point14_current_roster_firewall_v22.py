from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.player_expected_xi import (
    FORMATION_SLOTS,
    normalize_position,
    positional_fit,
    resolve_candidate,
)
from scripts.player_expected_xi_candidate_pool import (
    broad_roster_position,
    documented_slot_from_grid,
    parse_xi,
    prior_team_lineups,
    read_csv,
)

OPS = Path("ops")
ROSTERS = OPS / "team_rosters.csv"
HIST_LINEUPS = OPS / "historical_lineup_snapshots.csv"
LIVE_LINEUPS = OPS / "lineup_snapshots.csv"
AVAILABILITY = OPS / "player_availability_prematch_events.csv"
DISCIPLINE = OPS / "player_discipline_prematch_events.csv"
OFFICIAL_CURRENT = OPS / "point14_current_official_availability.csv"
OUT = OPS / "point14_current_expected_xi_v22.json"

AS_OF_UTC = "2026-09-27T12:00:00+00:00"
TARGETS = [
    {"team_id": "33", "team_name": "Manchester United", "formation": "4-2-3-1", "competition": "39"},
    {"team_id": "47", "team_name": "Tottenham", "formation": "4-2-3-1", "competition": "39"},
]

MAX_STABLE_ROSTER_AGE_DAYS = 28
MIN_EXACT_FIT_RANK = 3


def _s(v: Any) -> str:
    return str(v if v is not None else "").strip()


def _dt(v: Any) -> datetime | None:
    try:
        d = datetime.fromisoformat(_s(v).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d.astimezone(timezone.utc) if d.tzinfo else None


def latest_roster_snapshot(rows, *, team_id, as_of_utc):
    cutoff = _dt(as_of_utc)
    eligible = []
    for row in rows:
        if _s(row.get("team_id")) != _s(team_id):
            continue
        captured = _dt(row.get("captured_at_utc"))
        if not cutoff or not captured or captured > cutoff:
            continue
        eligible.append((captured, row))
    if not eligible:
        return {"status": "CURRENT_ROSTER_EVIDENCE_MISSING", "rows": []}

    stamp = max(x[0] for x in eligible)
    latest = [row for captured, row in eligible if captured == stamp]
    age_days = (cutoff - stamp).total_seconds() / 86400.0

    return {
        "status": (
            "CURRENT_ROSTER_FRESH"
            if age_days <= MAX_STABLE_ROSTER_AGE_DAYS
            else "CURRENT_ROSTER_STALE"
        ),
        "captured_at_utc": stamp.isoformat().replace("+00:00", "Z"),
        "age_days": round(age_days, 3),
        "player_count": len(latest),
        "rows": latest,
    }


def _usage_from_lineups(lineups):
    usage = {}
    for idx, row in enumerate(lineups):
        formation = _s(row.get("formation"))
        for p in row.get("xi", []):
            pid = _s(p.get("player_id"))
            if not pid:
                continue
            slot = documented_slot_from_grid(formation, p.get("grid"))
            state = usage.setdefault(pid, {
                "player_id": pid,
                "player_name": _s(p.get("player_name")),
                "starts_last_5": 0,
                "starts_last_10": 0,
                "documented_positions": [],
                "latest_fixture_rank": 9999,
            })
            if idx < 5:
                state["starts_last_5"] += 1
            if idx < 10:
                state["starts_last_10"] += 1
            state["latest_fixture_rank"] = min(state["latest_fixture_rank"], idx)
            if slot and slot not in state["documented_positions"]:
                state["documented_positions"].append(slot)
    return usage


def _official_events(rows, *, team_id, before_utc):
    cutoff = _dt(before_utc)
    by_player = {}
    for row in rows:
        if _s(row.get("team_id")) != _s(team_id):
            continue
        observed = _dt(row.get("observed_at_utc"))
        if not observed or not cutoff or observed > cutoff:
            continue
        pid = _s(row.get("player_id"))
        if not pid:
            continue
        by_player.setdefault(pid, []).append({
            "player_id": pid,
            "team_id": _s(team_id),
            "event_type": _s(row.get("event_type")).upper(),
            "status": _s(row.get("status")).upper(),
            "competition_scope": _s(row.get("competition_scope")),
            "observed_at_utc": _s(row.get("observed_at_utc")),
            "source": _s(row.get("source")),
        })
    for events in by_player.values():
        events.sort(key=lambda x: x["observed_at_utc"])
    return by_player


def _journal_events(rows, *, team_id, before_utc):
    cutoff = _dt(before_utc)
    by_player = {}
    for row in rows:
        if _s(row.get("team_id")) != _s(team_id):
            continue
        observed = _dt(row.get("observed_at_utc"))
        if not observed or not cutoff or observed > cutoff:
            continue
        pid = _s(row.get("player_id"))
        if not pid:
            continue
        state = _s(row.get("state")).upper()
        availability_type = _s(row.get("availability_type")).upper()
        if state == "PRESENT":
            event_type, status = "AVAILABILITY", "PRESENT"
        elif state == "ABSENT":
            event_type = "INJURY"
            status = "QUESTIONABLE" if availability_type == "QUESTIONABLE" else "CONFIRMED_INJURY_OUT"
        else:
            continue
        by_player.setdefault(pid, []).append({
            "player_id": pid,
            "team_id": _s(team_id),
            "event_type": event_type,
            "status": status,
            "competition_scope": "",
            "observed_at_utc": _s(row.get("observed_at_utc")),
            "source": _s(row.get("source")),
        })
    return by_player


def build_candidates(*, team_id, as_of_utc, roster_rows, lineup_rows, availability_rows, official_rows):
    roster = latest_roster_snapshot(roster_rows, team_id=team_id, as_of_utc=as_of_utc)
    if roster["status"] != "CURRENT_ROSTER_FRESH":
        return roster, []

    lineups = prior_team_lineups(lineup_rows, team_id=team_id, before_utc=as_of_utc)
    usage = _usage_from_lineups(lineups)
    journal = _journal_events(availability_rows, team_id=team_id, before_utc=as_of_utc)
    official = _official_events(official_rows, team_id=team_id, before_utc=as_of_utc)

    candidates = []
    for row in roster["rows"]:
        pid = _s(row.get("player_id"))
        if not pid:
            continue
        u = usage.get(pid, {})
        documented = list(u.get("documented_positions") or [])
        roster_group = broad_roster_position(row.get("position"))
        candidates.append({
            "player_id": pid,
            "player_name": _s(row.get("player_name")),
            "primary_position": documented[0] if documented else roster_group,
            "documented_positions": documented,
            "roster_position": roster_group,
            "roster_captured_at_utc": _s(row.get("captured_at_utc")),
            "starts_last_5": int(u.get("starts_last_5", 0)),
            "starts_last_10": int(u.get("starts_last_10", 0)),
            "latest_fixture_rank": int(u.get("latest_fixture_rank", 9999)),
            "availability_events": (journal.get(pid, []) + official.get(pid, [])),
        })
    return roster, candidates


def strict_expected_xi(candidates, *, formation, team_id, competition, as_of_utc):
    slots = list(FORMATION_SLOTS[formation])
    selected = set()
    assignments = {}
    unresolved = []

    indexed = list(enumerate(slots))

    def options(index_slot):
        _, slot = index_slot
        count = 0
        for c in candidates:
            if _s(c.get("player_id")) in selected:
                continue
            fit = positional_fit(c, slot)
            if fit["fit_rank"] >= MIN_EXACT_FIT_RANK:
                count += 1
        return count

    indexed.sort(key=lambda item: (options(item), item[0]))

    for idx, slot in indexed:
        ranked = []
        for c in candidates:
            pid = _s(c.get("player_id"))
            if not pid or pid in selected:
                continue
            fit = positional_fit(c, slot)
            if fit["fit_rank"] < MIN_EXACT_FIT_RANK:
                continue
            resolved = resolve_candidate(
                c,
                team_id=team_id,
                target_competition=competition,
                before_utc=as_of_utc,
            )
            if resolved["availability"]["availability_status"] == "UNAVAILABLE":
                continue
            ranked.append((resolved, fit))

        ranked.sort(
            key=lambda item: (
                item[0]["availability"]["availability_status"] == "AVAILABLE",
                item[1]["fit_rank"],
                int(item[0].get("starts_last_10", 0)),
                int(item[0].get("starts_last_5", 0)),
                -int(item[0].get("latest_fixture_rank", 9999)),
                _s(item[0].get("player_id")),
            ),
            reverse=True,
        )

        if not ranked:
            unresolved.append({"slot_index": idx, "slot": slot, "reason": "NO_CURRENT_ROSTER_EXACT_ROLE_CANDIDATE"})
            continue

        chosen, fit = ranked[0]
        pid = _s(chosen.get("player_id"))
        selected.add(pid)
        assignments[idx] = {
            "slot_index": idx,
            "slot": slot,
            "player_id": pid,
            "player_name": _s(chosen.get("player_name")),
            "availability_status": chosen["availability"]["availability_status"],
            "availability_reason": chosen["availability"]["resolution_reason"],
            "fit_level": fit["fit_level"],
            "starts_last_5": int(chosen.get("starts_last_5", 0)),
            "starts_last_10": int(chosen.get("starts_last_10", 0)),
            "roster_captured_at_utc": _s(chosen.get("roster_captured_at_utc")),
            "start_probability": None,
            "start_probability_status": "UNCALIBRATED",
        }

    xi = [assignments[i] for i in range(11) if i in assignments]
    return {
        "status": "EXPECTED_XI_CURRENT_ROSTER_COMPLETE" if len(xi) == 11 else "EXPECTED_XI_CURRENT_ROSTER_UNRESOLVED",
        "expected_xi_count": len(xi),
        "expected_xi": xi,
        "unresolved_slots": sorted(unresolved, key=lambda x: x["slot_index"]),
        "selection_policy": "CURRENT_ROSTER_HARD_GATE_THEN_AVAILABILITY_THEN_EXACT_DOCUMENTED_ROLE_THEN_RECENT_USAGE",
        "probability_status": "UNCALIBRATED",
        "operational_betting_authority": False,
        "research_only": True,
    }


def main():
    roster_rows = read_csv(ROSTERS)
    lineup_rows = read_csv(HIST_LINEUPS) + read_csv(LIVE_LINEUPS)
    availability_rows = read_csv(AVAILABILITY)
    official_rows = read_csv(OFFICIAL_CURRENT)

    output = {
        "version": "PBK_POINT14_CURRENT_ROSTER_FIREWALL_V22",
        "as_of_utc": AS_OF_UTC,
        "current_roster_is_hard_gate": True,
        "historical_lineup_membership_cannot_override_current_roster": True,
        "teams": [],
        "probability_status": "UNCALIBRATED",
        "research_only": True,
        "operational_betting_authority": False,
    }

    for target in TARGETS:
        roster, candidates = build_candidates(
            team_id=target["team_id"],
            as_of_utc=AS_OF_UTC,
            roster_rows=roster_rows,
            lineup_rows=lineup_rows,
            availability_rows=availability_rows,
            official_rows=official_rows,
        )
        xi = strict_expected_xi(
            candidates,
            formation=target["formation"],
            team_id=target["team_id"],
            competition=target["competition"],
            as_of_utc=AS_OF_UTC,
        )
        output["teams"].append({
            **target,
            "roster_status": roster["status"],
            "roster_captured_at_utc": roster.get("captured_at_utc"),
            "roster_age_days": roster.get("age_days"),
            "current_roster_player_count": roster.get("player_count", 0),
            **xi,
        })

    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=" * 100)
    print("PBK POINT14 V22 — CURRENT ROSTER HARD FIREWALL -> EXPECTED XI")
    print("=" * 100)
    for team in output["teams"]:
        print(
            f"{team['team_id']} {team['team_name']} | roster={team['roster_status']} "
            f"@ {team['roster_captured_at_utc']} | xi={team['status']} {team['expected_xi_count']}/11"
        )
        for p in team["expected_xi"]:
            print(
                f"  {p['slot']:<3} {p['player_name']} | avail={p['availability_status']} "
                f"| starts10={p['starts_last_10']} | fit={p['fit_level']}"
            )
        for u in team["unresolved_slots"]:
            print(f"  UNRESOLVED {u['slot']}: {u['reason']}")
    print()
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print()
    print("POINT14 CURRENT ROSTER FIREWALL V22 PASSED")


if __name__ == "__main__":
    main()
