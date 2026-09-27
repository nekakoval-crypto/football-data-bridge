from __future__ import annotations

import csv
import itertools
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path


TENURE_PATH = Path("ops/coach_tenure_history.csv")
LINEUP_PATH = Path("ops/historical_lineup_snapshots.csv")
OUT_PATH = Path("ops/point14_in_tenure_xi_composition_v20.json")

VERIFIED_AUTHORITY = "HISTORICAL_VERIFIED"
COMPLETE_XI_COUNT = 11
CORE_START_RATE = 0.60
MIN_ANALYZABLE_FIXTURES = 5


def _s(value):
    return str(value if value is not None else "").strip()


def _parse_date(value):
    text = _s(value)
    return date.fromisoformat(text[:10]) if text else None


def _parse_dt(value):
    text = _s(value)
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def _parse_xi(value):
    if not value:
        return []
    try:
        items = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(items, list) or len(items) != COMPLETE_XI_COUNT:
        return []
    output = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            return []
        pid = _s(item.get("id"))
        name = _s(item.get("name"))
        if not pid or pid in seen:
            return []
        seen.add(pid)
        output.append({
            "player_id": pid,
            "player_name": name or None,
            "pos": _s(item.get("pos")) or None,
            "grid": _s(item.get("grid")) or None,
        })
    return output


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def conservative_in_tenure(kickoff_utc, tenure_row):
    kickoff = _parse_dt(kickoff_utc)
    if kickoff is None:
        return False
    start = _parse_date(tenure_row.get("valid_from_utc"))
    end = _parse_date(tenure_row.get("valid_to_utc"))
    precision = _s(tenure_row.get("effective_precision")).upper()
    if start is None:
        return False

    kdate = kickoff.date()
    if precision == "DATE":
        if kdate <= start:
            return False
    elif kdate < start:
        return False

    if end is not None:
        if precision == "DATE":
            if kdate >= end:
                return False
        elif kdate > end:
            return False
    return True


def _complete_team_rows(tenure_row, lineup_rows):
    team_id = _s(tenure_row.get("team_id"))
    rows = []
    for row in lineup_rows:
        if _s(row.get("team_id")) != team_id:
            continue
        if not conservative_in_tenure(row.get("kickoff_utc"), tenure_row):
            continue
        xi = _parse_xi(row.get("starting_xi_json"))
        if len(xi) != COMPLETE_XI_COUNT:
            continue
        if int(_s(row.get("starting_xi_count")) or 0) != COMPLETE_XI_COUNT:
            continue
        rows.append({**row, "_xi": xi})

    dedup = {}
    for row in rows:
        fid = _s(row.get("fixture_id"))
        if not fid:
            continue
        # historical archive may contain duplicate captures; keep latest retrieval
        key = (_s(row.get("retrieved_at_utc")), _s(row.get("kickoff_utc")))
        if fid not in dedup or key > dedup[fid][0]:
            dedup[fid] = (key, row)

    output = [item[1] for item in dedup.values()]
    output.sort(key=lambda row: (_s(row.get("kickoff_utc")), _s(row.get("fixture_id"))))
    return output


def audit_team(tenure_row, lineup_rows):
    fixtures = _complete_team_rows(tenure_row, lineup_rows)
    n = len(fixtures)

    if n == 0:
        evidence_status = "CURRENT_XI_EVIDENCE_MISSING"
    elif n < MIN_ANALYZABLE_FIXTURES:
        evidence_status = "CURRENT_XI_EVIDENCE_PRELIMINARY"
    else:
        evidence_status = "CURRENT_XI_EVIDENCE_ANALYZABLE"

    starts = Counter()
    names = {}
    positions = defaultdict(Counter)
    pair_starts = Counter()
    formation_player_starts = defaultdict(Counter)
    fixture_payloads = []

    for row in fixtures:
        xi = row["_xi"]
        ids = [p["player_id"] for p in xi]
        formation = _s(row.get("formation")) or None

        for player in xi:
            pid = player["player_id"]
            starts[pid] += 1
            if player.get("player_name"):
                names[pid] = player["player_name"]
            if player.get("pos"):
                positions[pid][player["pos"]] += 1
            if formation:
                formation_player_starts[formation][pid] += 1

        for a, b in itertools.combinations(sorted(ids), 2):
            pair_starts[(a, b)] += 1

        fixture_payloads.append({
            "fixture_id": _s(row.get("fixture_id")),
            "kickoff_utc": _s(row.get("kickoff_utc")),
            "home_team": _s(row.get("home_team")),
            "away_team": _s(row.get("away_team")),
            "formation": formation,
            "starter_ids": ids,
            "starter_names": [names.get(pid) for pid in ids],
        })

    core_threshold = math.ceil(n * CORE_START_RATE) if n else None
    players = []
    for pid, count in starts.most_common():
        players.append({
            "player_id": pid,
            "player_name": names.get(pid),
            "starts": count,
            "start_rate": round(count / n, 4) if n else None,
            "core_60pct": bool(core_threshold and count >= core_threshold),
            "ever_present": count == n if n else False,
            "observed_positions": [
                {"pos": pos, "starts": cnt}
                for pos, cnt in positions[pid].most_common()
            ],
        })

    overlaps = []
    for prev, curr in zip(fixture_payloads, fixture_payloads[1:]):
        a = set(prev["starter_ids"])
        b = set(curr["starter_ids"])
        overlap = len(a & b)
        overlaps.append({
            "from_fixture_id": prev["fixture_id"],
            "to_fixture_id": curr["fixture_id"],
            "shared_starters": overlap,
            "starter_changes": COMPLETE_XI_COUNT - overlap,
            "jaccard": round(overlap / len(a | b), 4),
        })

    pair_rows = []
    for (a, b), count in pair_starts.most_common(30):
        pair_rows.append({
            "player_a_id": a,
            "player_a_name": names.get(a),
            "player_b_id": b,
            "player_b_name": names.get(b),
            "joint_starts": count,
            "joint_start_rate": round(count / n, 4) if n else None,
        })

    formation_profiles = []
    for formation, counter in sorted(
        formation_player_starts.items(),
        key=lambda item: (-sum(item[1].values()), item[0]),
    ):
        match_count = sum(1 for row in fixture_payloads if row["formation"] == formation)
        formation_profiles.append({
            "formation": formation,
            "matches": match_count,
            "top_starters": [
                {
                    "player_id": pid,
                    "player_name": names.get(pid),
                    "starts_in_formation": count,
                    "formation_start_rate": round(count / match_count, 4) if match_count else None,
                }
                for pid, count in counter.most_common(15)
            ],
        })

    overlap_values = [row["shared_starters"] for row in overlaps]

    return {
        "team_id": _s(tenure_row.get("team_id")),
        "team_name": _s(tenure_row.get("team_name")),
        "verified_coach_name": _s(tenure_row.get("coach_name")),
        "verified_valid_from_utc": _s(tenure_row.get("valid_from_utc")),
        "effective_precision": _s(tenure_row.get("effective_precision")),
        "evidence_status": evidence_status,
        "distinct_complete_fixtures": n,
        "unique_starters": len(starts),
        "core_threshold_rule": "starts >= ceil(0.60 * complete fixtures)",
        "core_threshold_starts": core_threshold,
        "players": players,
        "top_pairs": pair_rows,
        "consecutive_lineup_overlap": {
            "comparisons": len(overlaps),
            "mean_shared_starters": (
                round(sum(overlap_values) / len(overlap_values), 3)
                if overlap_values else None
            ),
            "min_shared_starters": min(overlap_values) if overlap_values else None,
            "max_shared_starters": max(overlap_values) if overlap_values else None,
            "transitions": overlaps,
        },
        "formation_profiles": formation_profiles,
        "fixtures": fixture_payloads,
        "coach_metadata_used_as_tenure_truth": False,
        "descriptive_only": True,
        "creates_signal": False,
        "automatic_tactical_regime_promotion": False,
        "operational_betting_authority": False,
        "research_only": True,
    }


def build_audit(tenure_rows, lineup_rows):
    verified = [
        row for row in tenure_rows
        if _s(row.get("temporal_authority")).upper() == VERIFIED_AUTHORITY
    ]
    teams = [audit_team(row, lineup_rows) for row in verified]
    return {
        "version": "PBK_POINT14_IN_TENURE_XI_COMPOSITION_V20",
        "verified_tenure_count": len(verified),
        "lineup_source": "ops/historical_lineup_snapshots.csv",
        "lineup_coach_metadata_authority": "RETROSPECTIVE_ONLY",
        "core_start_rate": CORE_START_RATE,
        "min_analyzable_fixtures": MIN_ANALYZABLE_FIXTURES,
        "teams": teams,
        "provider_polling": False,
        "coach_tenure_mutation": False,
        "descriptive_only": True,
        "creates_signal": False,
        "automatic_tactical_regime_promotion": False,
        "operational_betting_authority": False,
        "research_only": True,
    }


def main():
    result = build_audit(read_csv(TENURE_PATH), read_csv(LINEUP_PATH))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("=" * 100)
    print("PBK POINT 14G V20 — VERIFIED TENURE -> STARTING XI COMPOSITION AUDIT")
    print("=" * 100)
    for team in result["teams"]:
        core = [
            p["player_name"] or p["player_id"]
            for p in team["players"]
            if p["core_60pct"]
        ]
        overlap = team["consecutive_lineup_overlap"]["mean_shared_starters"]
        print(
            f"{team['team_id']} {team['team_name']} | "
            f"coach={team['verified_coach_name']} | "
            f"status={team['evidence_status']} | "
            f"fixtures={team['distinct_complete_fixtures']} | "
            f"unique_starters={team['unique_starters']} | "
            f"core60={len(core)} | mean_overlap={overlap}"
        )
        print("  core:", ", ".join(core) if core else "NONE")

    print()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print("POINT14 IN-TENURE XI COMPOSITION V20 PASSED")


if __name__ == "__main__":
    main()
