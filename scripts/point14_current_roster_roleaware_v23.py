from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any

from scripts.player_expected_xi import FORMATION_SLOTS, positional_fit, resolve_candidate
from scripts.player_expected_xi_candidate_pool import documented_slot_from_grid, parse_xi, read_csv

OPS = Path("ops")
ROSTERS = OPS / "team_rosters.csv"
HIST_LINEUPS = OPS / "historical_lineup_snapshots.csv"
LIVE_LINEUPS = OPS / "lineup_snapshots.csv"
TENURES = OPS / "coach_tenure_history.csv"
AVAILABILITY = OPS / "player_availability_prematch_events.csv"
OFFICIAL_CURRENT = OPS / "point14_current_official_availability.csv"
OUT = OPS / "point14_current_expected_xi_v23.json"

AS_OF_UTC = "2026-09-27T12:00:00+00:00"
TARGETS = [
    {"team_id": "33", "team_name": "Manchester United", "formation": "4-2-3-1", "competition": "39"},
    {"team_id": "47", "team_name": "Tottenham", "formation": "4-2-3-1", "competition": "39"},
]
MAX_STABLE_ROSTER_AGE_DAYS = 28
SEASON_START = date(2026, 7, 1)


def _s(v: Any) -> str:
    return str(v if v is not None else "").strip()


def _dt(v: Any) -> datetime | None:
    try:
        d = datetime.fromisoformat(_s(v).replace("Z", "+00:00"))
    except Exception:
        return None
    return d.astimezone(timezone.utc) if d.tzinfo else None


def _date(v: Any) -> date | None:
    t = _s(v)
    try:
        return date.fromisoformat(t[:10]) if t else None
    except Exception:
        return None


def latest_roster_snapshot(rows, team_id, as_of_utc):
    cutoff = _dt(as_of_utc)
    eligible = []
    for r in rows:
        if _s(r.get("team_id")) != _s(team_id):
            continue
        cap = _dt(r.get("captured_at_utc"))
        if cap and cutoff and cap <= cutoff:
            eligible.append((cap, r))
    if not eligible:
        return {"status": "CURRENT_ROSTER_EVIDENCE_MISSING", "rows": []}
    stamp = max(c for c, _ in eligible)
    latest = [r for c, r in eligible if c == stamp]
    age = (cutoff - stamp).total_seconds() / 86400.0
    return {
        "status": "CURRENT_ROSTER_FRESH" if age <= MAX_STABLE_ROSTER_AGE_DAYS else "CURRENT_ROSTER_STALE",
        "captured_at_utc": stamp.isoformat().replace("+00:00", "Z"),
        "age_days": round(age, 3),
        "rows": latest,
    }


def verified_tenure(tenures, team_id):
    rows = [
        r for r in tenures
        if _s(r.get("team_id")) == _s(team_id)
        and _s(r.get("temporal_authority")).upper() == "HISTORICAL_VERIFIED"
    ]
    return rows[-1] if rows else None


def in_verified_tenure(row, tenure):
    if not tenure:
        return False
    kd = _date(row.get("kickoff_utc"))
    start = _date(tenure.get("valid_from_utc"))
    end = _date(tenure.get("valid_to_utc"))
    if not kd or not start:
        return False
    precision = _s(tenure.get("effective_precision")).upper()
    if precision == "DATE":
        if kd <= start:
            return False
        if end and kd >= end:
            return False
    else:
        if kd < start:
            return False
        if end and kd > end:
            return False
    return True


def dedup_lineups(rows):
    best = {}
    for r in rows:
        fid = _s(r.get("fixture_id"))
        if not fid:
            continue
        stamp = _s(r.get("retrieved_at_utc") or r.get("captured_at_utc"))
        if fid not in best or stamp > best[fid][0]:
            best[fid] = (stamp, r)
    out = [x[1] for x in best.values()]
    out.sort(key=lambda r: _s(r.get("kickoff_utc")), reverse=True)
    return out


def role_history_all_clubs(all_lineups):
    roles = {}
    for r in all_lineups:
        formation = _s(r.get("formation"))
        for p in parse_xi(r.get("starting_xi_json")):
            pid = _s(p.get("player_id"))
            slot = documented_slot_from_grid(formation, p.get("grid"))
            if not pid or not slot:
                continue
            state = roles.setdefault(pid, Counter())
            state[slot] += 1
    return roles


def usage_for_team(all_lineups, tenures, team_id):
    team_rows = [r for r in all_lineups if _s(r.get("team_id")) == _s(team_id)]
    team_rows = dedup_lineups(team_rows)

    current_season = [r for r in team_rows if (_date(r.get("kickoff_utc")) or date.min) >= SEASON_START]
    if current_season:
        source = "CURRENT_SEASON"
        rows = current_season
    else:
        tenure = verified_tenure(tenures, team_id)
        rows = [r for r in team_rows if in_verified_tenure(r, tenure)]
        source = "VERIFIED_TENURE_FALLBACK"

    usage = {}
    for idx, r in enumerate(rows):
        formation = _s(r.get("formation"))
        for p in parse_xi(r.get("starting_xi_json")):
            pid = _s(p.get("player_id"))
            if not pid:
                continue
            slot = documented_slot_from_grid(formation, p.get("grid"))
            st = usage.setdefault(pid, {"starts10": 0, "starts5": 0, "roles": Counter()})
            if idx < 10:
                st["starts10"] += 1
            if idx < 5:
                st["starts5"] += 1
            if slot:
                st["roles"][slot] += 1
    return source, usage


def official_events(rows, team_id, before_utc):
    cutoff = _dt(before_utc)
    out = {}
    for r in rows:
        if _s(r.get("team_id")) != _s(team_id):
            continue
        observed = _dt(r.get("observed_at_utc"))
        if not observed or not cutoff or observed > cutoff:
            continue
        pid = _s(r.get("player_id"))
        if not pid:
            continue
        out.setdefault(pid, []).append({
            "player_id": pid,
            "team_id": _s(team_id),
            "event_type": _s(r.get("event_type")).upper(),
            "status": _s(r.get("status")).upper(),
            "competition_scope": _s(r.get("competition_scope")),
            "observed_at_utc": _s(r.get("observed_at_utc")),
            "source": _s(r.get("source")),
        })
    return out


def journal_events(rows, team_id, before_utc):
    cutoff = _dt(before_utc)
    out = {}
    for r in rows:
        if _s(r.get("team_id")) != _s(team_id):
            continue
        observed = _dt(r.get("observed_at_utc"))
        if not observed or not cutoff or observed > cutoff:
            continue
        pid = _s(r.get("player_id"))
        if not pid:
            continue
        state = _s(r.get("state")).upper()
        at = _s(r.get("availability_type")).upper()
        if state == "PRESENT":
            event_type, status = "AVAILABILITY", "PRESENT"
        elif state == "ABSENT":
            event_type = "INJURY"
            status = "QUESTIONABLE" if at == "QUESTIONABLE" else "CONFIRMED_INJURY_OUT"
        else:
            continue
        out.setdefault(pid, []).append({
            "player_id": pid,
            "team_id": _s(team_id),
            "event_type": event_type,
            "status": status,
            "competition_scope": "",
            "observed_at_utc": _s(r.get("observed_at_utc")),
            "source": _s(r.get("source")),
        })
    return out


def build_team(target, roster_rows, all_lineups, tenures, availability_rows, official_rows, global_roles):
    roster = latest_roster_snapshot(roster_rows, target["team_id"], AS_OF_UTC)
    if roster["status"] != "CURRENT_ROSTER_FRESH":
        return {**target, "roster_status": roster["status"], "status": "EXPECTED_XI_UNRESOLVED", "expected_xi": []}

    usage_source, usage = usage_for_team(all_lineups, tenures, target["team_id"])
    j = journal_events(availability_rows, target["team_id"], AS_OF_UTC)
    o = official_events(official_rows, target["team_id"], AS_OF_UTC)

    candidates = []
    for r in roster["rows"]:
        pid = _s(r.get("player_id"))
        if not pid:
            continue
        u = usage.get(pid, {"starts10": 0, "starts5": 0, "roles": Counter()})
        role_counts = Counter(global_roles.get(pid, Counter()))
        role_counts.update(u["roles"])
        documented = [slot for slot, _ in role_counts.most_common()]
        candidates.append({
            "player_id": pid,
            "player_name": _s(r.get("player_name")),
            "primary_position": documented[0] if documented else "",
            "documented_positions": documented,
            "starts_last_10": u["starts10"],
            "starts_last_5": u["starts5"],
            "availability_events": j.get(pid, []) + o.get(pid, []),
            "roster_captured_at_utc": _s(r.get("captured_at_utc")),
        })

    slots = list(FORMATION_SLOTS.get(target["formation"], []))

    if len(slots) != 11:
        return {
            **target,
            "roster_status": roster["status"],
            "roster_captured_at_utc": roster.get("captured_at_utc"),
            "usage_source": usage_source,
            "status": "EXPECTED_XI_UNSUPPORTED_FORMATION",
            "expected_xi_count": 0,
            "expected_xi": [],
            "unresolved_slots": [
                {
                    "slot_index": None,
                    "slot": target["formation"],
                    "reason": "UNSUPPORTED_FORMATION",
                }
            ],
            "probability_status": "UNCALIBRATED",
            "research_only": True,
            "operational_betting_authority": False,
        }

    # Resolve availability once per player.
    resolved_candidates = []

    for candidate in sorted(
        candidates,
        key=lambda c: _s(c.get("player_id")),
    ):
        resolved = resolve_candidate(
            candidate,
            team_id=target["team_id"],
            target_competition=target["competition"],
            before_utc=AS_OF_UTC,
        )

        availability_status = (
            resolved["availability"]["availability_status"]
        )

        if availability_status == "UNAVAILABLE":
            continue

        availability_rank = {
            "AVAILABLE": 2,
            "UNCERTAIN": 1,
        }.get(availability_status, 0)

        resolved_candidates.append(
            {
                "player": resolved,
                "availability_rank": availability_rank,
            }
        )

    # Exact global assignment.
    #
    # State mask = which of the 11 tactical slots have been filled.
    # Each roster player is processed once, therefore one player cannot
    # occupy two positions.
    #
    # Score is lexicographic:
    #   1. number of filled slots
    #   2. total starts in last 5
    #   3. total starts in last 10
    #   4. total positional fit
    #   5. total availability confidence
    #
    # 2^11 = 2048 tactical states, so this is small and deterministic.
    dp = {
        0: (
            (0, 0, 0, 0, 0),
            (),
        )
    }

    def add_score(left, right):
        return tuple(
            a + b
            for a, b in zip(left, right)
        )

    for candidate_index, item in enumerate(resolved_candidates):

        player = item["player"]

        next_dp = dict(dp)

        for mask, (score, picks) in dp.items():

            for slot_index, slot in enumerate(slots):

                bit = 1 << slot_index

                if mask & bit:
                    continue

                fit = positional_fit(
                    player,
                    slot,
                )

                # Keep V23 conservative role rule:
                # PRIMARY_EXACT or DOCUMENTED_EXACT only.
                if fit["fit_rank"] < 3:
                    continue

                edge_score = (
                    1,
                    int(player.get("starts_last_5", 0)),
                    int(player.get("starts_last_10", 0)),
                    int(fit["fit_rank"]),
                    int(item["availability_rank"]),
                )

                new_mask = mask | bit

                new_score = add_score(
                    score,
                    edge_score,
                )

                new_picks = picks + (
                    (
                        slot_index,
                        candidate_index,
                        fit["fit_level"],
                    ),
                )

                old = next_dp.get(new_mask)

                if (
                    old is None
                    or new_score > old[0]
                ):
                    next_dp[new_mask] = (
                        new_score,
                        new_picks,
                    )

        dp = next_dp

    best_mask, (best_score, best_picks) = max(
        dp.items(),
        key=lambda item: (
            item[1][0],
            item[0],
        ),
    )

    assignments = {}

    for (
        slot_index,
        candidate_index,
        fit_level,
    ) in best_picks:

        item = resolved_candidates[candidate_index]

        chosen = item["player"]

        assignments[slot_index] = {
            "slot_index": slot_index,
            "slot": slots[slot_index],
            "player_id": _s(chosen.get("player_id")),
            "player_name": _s(chosen.get("player_name")),
            "availability_status": (
                chosen["availability"]["availability_status"]
            ),
            "availability_reason": (
                chosen["availability"]["resolution_reason"]
            ),
            "fit_level": fit_level,
            "starts_last_5": int(
                chosen.get("starts_last_5", 0)
            ),
            "starts_last_10": int(
                chosen.get("starts_last_10", 0)
            ),
            "start_probability": None,
            "start_probability_status": "UNCALIBRATED",
        }

    unresolved = []

    for slot_index, slot in enumerate(slots):

        if slot_index not in assignments:
            unresolved.append({
                "slot_index": slot_index,
                "slot": slot,
                "reason": "NO_GLOBAL_CURRENT_ROSTER_ASSIGNMENT",
            })

    xi = [
        assignments[i]
        for i in range(11)
        if i in assignments
    ]
    return {
        **target,
        "roster_status": roster["status"],
        "roster_captured_at_utc": roster["captured_at_utc"],
        "usage_source": usage_source,
        "status": "EXPECTED_XI_CURRENT_ROSTER_COMPLETE" if len(xi) == 11 else "EXPECTED_XI_CURRENT_ROSTER_UNRESOLVED",
        "expected_xi_count": len(xi),
        "expected_xi": xi,
        "unresolved_slots": unresolved,
        "probability_status": "UNCALIBRATED",
        "research_only": True,
        "operational_betting_authority": False,
    }


def main():
    roster_rows = read_csv(ROSTERS)
    all_lineups = read_csv(HIST_LINEUPS) + read_csv(LIVE_LINEUPS)
    tenures = read_csv(TENURES)
    availability_rows = read_csv(AVAILABILITY)
    official_rows = read_csv(OFFICIAL_CURRENT)
    global_roles = role_history_all_clubs(all_lineups)

    result = {
        "version": "PBK_POINT14_CURRENT_ROSTER_ROLE_AWARE_V23",
        "as_of_utc": AS_OF_UTC,
        "current_roster_hard_gate": True,
        "cross_club_role_history_allowed_for_role_evidence": True,
        "historical_membership_never_overrides_current_roster": True,
        "availability_uncertainty_preserved_not_auto_benched": True,
        "teams": [
            build_team(t, roster_rows, all_lineups, tenures, availability_rows, official_rows, global_roles)
            for t in TARGETS
        ],
        "probability_status": "UNCALIBRATED",
        "research_only": True,
        "operational_betting_authority": False,
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=" * 100)
    print("PBK POINT14 V23 — CURRENT ROSTER + CURRENT USAGE + CROSS-CLUB ROLE EVIDENCE")
    print("=" * 100)
    for team in result["teams"]:
        print(
            f"{team['team_id']} {team['team_name']} | usage={team.get('usage_source')} | "
            f"{team['status']} {team.get('expected_xi_count',0)}/11"
        )
        for p in team.get("expected_xi", []):
            print(
                f"  {p['slot']:<3} {p['player_name']} | avail={p['availability_status']} "
                f"| starts10={p['starts_last_10']} | fit={p['fit_level']}"
            )
        for u in team.get("unresolved_slots", []):
            print(f"  UNRESOLVED {u['slot']}: {u['reason']}")
    print()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print("POINT14 CURRENT ROSTER ROLE-AWARE V23 PASSED")


if __name__ == "__main__":
    main()
