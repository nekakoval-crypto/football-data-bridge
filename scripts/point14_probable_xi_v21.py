from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path


TENURE_PATH = Path("ops/coach_tenure_history.csv")
LINEUP_PATH = Path("ops/historical_lineup_snapshots.csv")
OUT_PATH = Path("ops/point14_probable_xi_v21.json")

VERIFIED_AUTHORITY = "HISTORICAL_VERIFIED"
COMPLETE_XI_COUNT = 11
RECENCY_DECAY = 0.85


def _s(v):
    return str(v if v is not None else "").strip()


def _parse_date(v):
    t = _s(v)
    return date.fromisoformat(t[:10]) if t else None


def _parse_dt(v):
    t = _s(v)
    return datetime.fromisoformat(t.replace("Z", "+00:00")) if t else None


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))


def _parse_xi(v):
    try:
        items = json.loads(v) if isinstance(v, str) else v
    except Exception:
        return []
    if not isinstance(items, list) or len(items) != 11:
        return []
    out = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            return []
        pid = _s(item.get("id"))
        if not pid or pid in seen:
            return []
        seen.add(pid)
        out.append({
            "player_id": pid,
            "player_name": _s(item.get("name")) or None,
            "pos": _s(item.get("pos")) or None,
            "grid": _s(item.get("grid")) or None,
        })
    return out


def conservative_in_tenure(kickoff_utc, tenure_row):
    kickoff = _parse_dt(kickoff_utc)
    if kickoff is None:
        return False
    start = _parse_date(tenure_row.get("valid_from_utc"))
    end = _parse_date(tenure_row.get("valid_to_utc"))
    precision = _s(tenure_row.get("effective_precision")).upper()
    if start is None:
        return False
    kd = kickoff.date()
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


def _team_rows(tenure_row, lineup_rows):
    tid = _s(tenure_row.get("team_id"))
    rows = []
    for row in lineup_rows:
        if _s(row.get("team_id")) != tid:
            continue
        if not conservative_in_tenure(row.get("kickoff_utc"), tenure_row):
            continue
        xi = _parse_xi(row.get("starting_xi_json"))
        if len(xi) != 11 or int(_s(row.get("starting_xi_count")) or 0) != 11:
            continue
        rows.append({**row, "_xi": xi})

    dedup = {}
    for row in rows:
        fid = _s(row.get("fixture_id"))
        if not fid:
            continue
        key = (_s(row.get("retrieved_at_utc")), _s(row.get("kickoff_utc")))
        if fid not in dedup or key > dedup[fid][0]:
            dedup[fid] = (key, row)

    out = [v[1] for v in dedup.values()]
    out.sort(key=lambda r: (_s(r.get("kickoff_utc")), _s(r.get("fixture_id"))))
    return out


def _grid_sort_key(grid):
    try:
        a, b = [int(x) for x in str(grid).split(":")]
        return (a, -b)
    except Exception:
        return (999, 999)


def probable_xi_for_team(tenure_row, lineup_rows):
    rows = _team_rows(tenure_row, lineup_rows)
    n = len(rows)

    if not rows:
        return {
            "team_id": _s(tenure_row.get("team_id")),
            "team_name": _s(tenure_row.get("team_name")),
            "coach_name": _s(tenure_row.get("coach_name")),
            "status": "EXPECTED_XI_EVIDENCE_MISSING",
            "expected_xi": [],
            "probability_status": "UNCALIBRATED",
        }

    formation_counts = Counter(_s(r.get("formation")) for r in rows if _s(r.get("formation")))
    latest_index = {}
    for i, r in enumerate(rows):
        latest_index[_s(r.get("formation"))] = i

    base_formation = sorted(
        formation_counts,
        key=lambda f: (-formation_counts[f], -latest_index.get(f, -1), f)
    )[0]

    formation_rows = [r for r in rows if _s(r.get("formation")) == base_formation]
    grid_counts = Counter()
    slot_candidates = defaultdict(dict)
    overall_starts = Counter()

    for idx, row in enumerate(rows):
        age = n - 1 - idx
        recency_w = RECENCY_DECAY ** age
        in_base = _s(row.get("formation")) == base_formation

        for p in row["_xi"]:
            overall_starts[p["player_id"]] += 1
            if not in_base or not p.get("grid"):
                continue
            grid = p["grid"]
            grid_counts[grid] += 1
            cur = slot_candidates[grid].get(p["player_id"])
            if cur is None:
                cur = {
                    "player_id": p["player_id"],
                    "player_name": p["player_name"],
                    "pos": p["pos"],
                    "slot_starts": 0,
                    "recency_score": 0.0,
                    "latest_start_index": -1,
                }
                slot_candidates[grid][p["player_id"]] = cur
            cur["slot_starts"] += 1
            cur["recency_score"] += recency_w
            cur["latest_start_index"] = idx

    grids = sorted(grid_counts.keys(), key=_grid_sort_key)
    selected = []
    used = set()

    for grid in grids:
        candidates = []
        for c in slot_candidates[grid].values():
            c = dict(c)
            c["overall_starts"] = overall_starts[c["player_id"]]
            candidates.append(c)

        candidates.sort(
            key=lambda c: (
                -c["slot_starts"],
                -c["recency_score"],
                -c["overall_starts"],
                -c["latest_start_index"],
                c["player_id"],
            )
        )

        pick = next((c for c in candidates if c["player_id"] not in used), None)
        if pick is None:
            continue

        used.add(pick["player_id"])
        selected.append({
            "grid": grid,
            "player_id": pick["player_id"],
            "player_name": pick["player_name"],
            "pos": pick["pos"],
            "slot_starts": pick["slot_starts"],
            "base_formation_matches": len(formation_rows),
            "slot_start_rate": round(pick["slot_starts"] / len(formation_rows), 4),
            "overall_tenure_starts": pick["overall_starts"],
            "tenure_start_rate": round(pick["overall_starts"] / n, 4),
            "selection_score_status": "DESCRIPTIVE_NOT_PROBABILITY",
        })

    status = (
        "EXPECTED_XI_READY_UNCALIBRATED"
        if len(selected) == 11
        else "EXPECTED_XI_UNRESOLVED"
    )

    return {
        "team_id": _s(tenure_row.get("team_id")),
        "team_name": _s(tenure_row.get("team_name")),
        "coach_name": _s(tenure_row.get("coach_name")),
        "verified_valid_from_utc": _s(tenure_row.get("valid_from_utc")),
        "status": status,
        "base_formation": base_formation,
        "complete_in_tenure_fixtures": n,
        "base_formation_matches": len(formation_rows),
        "formation_distribution": [
            {"formation": f, "matches": c}
            for f, c in formation_counts.most_common()
        ],
        "expected_xi": selected,
        "probability_status": "UNCALIBRATED",
        "creates_signal": False,
        "operational_betting_authority": False,
        "research_only": True,
    }


def build():
    tenures = read_csv(TENURE_PATH)
    lineups = read_csv(LINEUP_PATH)
    verified = [
        r for r in tenures
        if _s(r.get("temporal_authority")).upper() == VERIFIED_AUTHORITY
    ]
    return {
        "version": "PBK_POINT14_PROBABLE_XI_V21",
        "teams": [probable_xi_for_team(t, lineups) for t in verified],
        "probability_status": "UNCALIBRATED",
        "no_fake_probabilities": True,
        "provider_polling": False,
        "research_only": True,
        "operational_betting_authority": False,
    }


def main():
    result = build()
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("=" * 100)
    print("PBK POINT 14G V21 — PROBABLE XI FROM VERIFIED-TENURE LINEUP EVIDENCE")
    print("=" * 100)
    for team in result["teams"]:
        print(
            f"{team['team_id']} {team['team_name']} | "
            f"coach={team['coach_name']} | "
            f"formation={team.get('base_formation')} | "
            f"status={team['status']}"
        )
        for p in team["expected_xi"]:
            print(
                f"  {p['grid']:>4}  {p['player_name']} | "
                f"slot={p['slot_starts']}/{p['base_formation_matches']} | "
                f"tenure={p['overall_tenure_starts']}/{team['complete_in_tenure_fixtures']}"
            )
    print()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print("POINT14 PROBABLE XI V21 PASSED")


if __name__ == "__main__":
    main()
