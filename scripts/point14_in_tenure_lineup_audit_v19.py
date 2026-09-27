from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path


TENURE_PATH = Path("ops/coach_tenure_history.csv")
LINEUP_PATH = Path("ops/historical_lineup_snapshots.csv")
OUT_PATH = Path("ops/point14_in_tenure_lineup_audit_v19.json")

VERIFIED_AUTHORITY = "HISTORICAL_VERIFIED"
COMPLETE_XI_COUNT = 11
MIN_EVIDENCE_FIXTURES = 3


def _s(value):
    return str(value if value is not None else "").strip()


def _parse_date(value):
    text = _s(value)
    if not text:
        return None
    return date.fromisoformat(text[:10])


def _parse_dt(value):
    text = _s(value)
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


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

    # DATE precision never pretends that the appointment began at midnight.
    # Same-day fixtures stay boundary-uncertain and are excluded.
    if precision == "DATE":
        if kdate <= start:
            return False
    else:
        if kdate < start:
            return False

    if end is not None:
        if precision == "DATE":
            if kdate >= end:
                return False
        elif kdate > end:
            return False

    return True


def audit_team(tenure_row, lineup_rows):
    team_id = _s(tenure_row.get("team_id"))

    team_rows = [
        row for row in lineup_rows
        if _s(row.get("team_id")) == team_id
        and conservative_in_tenure(row.get("kickoff_utc"), tenure_row)
    ]

    complete = [
        row for row in team_rows
        if _s(row.get("formation"))
        and int(_s(row.get("starting_xi_count")) or 0) == COMPLETE_XI_COUNT
    ]

    fixture_ids = sorted({_s(row.get("fixture_id")) for row in complete if _s(row.get("fixture_id"))})
    formations = Counter(_s(row.get("formation")) for row in complete if _s(row.get("formation")))

    if not complete:
        status = "CURRENT_REGIME_FORMATION_EVIDENCE_MISSING"
    elif len(fixture_ids) < MIN_EVIDENCE_FIXTURES:
        status = "CURRENT_REGIME_FORMATION_EVIDENCE_INSUFFICIENT"
    else:
        status = "CURRENT_REGIME_FORMATION_EVIDENCE_AVAILABLE"

    ordered_formations = [
        {"formation": formation, "matches": matches}
        for formation, matches in sorted(
            formations.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    latest = sorted(
        complete,
        key=lambda row: (_s(row.get("kickoff_utc")), _s(row.get("fixture_id"))),
        reverse=True,
    )[:10]

    return {
        "team_id": team_id,
        "team_name": _s(tenure_row.get("team_name")),
        "verified_coach_name": _s(tenure_row.get("coach_name")),
        "verified_valid_from_utc": _s(tenure_row.get("valid_from_utc")),
        "effective_precision": _s(tenure_row.get("effective_precision")),
        "status": status,
        "in_tenure_lineup_rows": len(team_rows),
        "complete_in_tenure_lineup_rows": len(complete),
        "distinct_complete_fixtures": len(fixture_ids),
        "formation_distribution": ordered_formations,
        "latest_complete_lineups": [
            {
                "fixture_id": _s(row.get("fixture_id")),
                "kickoff_utc": _s(row.get("kickoff_utc")),
                "opponent_home": _s(row.get("home_team")),
                "opponent_away": _s(row.get("away_team")),
                "formation": _s(row.get("formation")),
                "starting_xi_count": int(_s(row.get("starting_xi_count")) or 0),
                # Provider coach metadata is deliberately exposed only as retrospective metadata.
                "provider_coach_name_retrospective_only": _s(row.get("coach_name")),
                "lineup_temporal_authority": _s(row.get("temporal_authority")),
            }
            for row in latest
        ],
        "coach_metadata_used_as_tenure_truth": False,
        "formation_used_as_match_evidence": True,
        "research_only": True,
        "operational_betting_authority": False,
    }


def build_audit(tenure_rows, lineup_rows):
    verified = [
        row for row in tenure_rows
        if _s(row.get("temporal_authority")).upper() == VERIFIED_AUTHORITY
    ]

    teams = [audit_team(row, lineup_rows) for row in verified]

    return {
        "version": "PBK_POINT14_IN_TENURE_LINEUP_AUDIT_V19",
        "verified_tenure_count": len(verified),
        "lineup_source": "ops/historical_lineup_snapshots.csv",
        "lineup_coach_metadata_authority": "RETROSPECTIVE_ONLY",
        "same_day_date_precision_policy": "EXCLUDE_BOUNDARY_DAY",
        "minimum_evidence_fixtures": MIN_EVIDENCE_FIXTURES,
        "teams": teams,
        "coach_tenure_mutation": False,
        "provider_polling": False,
        "automatic_regime_promotion": False,
        "research_only": True,
        "operational_betting_authority": False,
    }


def main():
    tenure_rows = read_csv(TENURE_PATH)
    lineup_rows = read_csv(LINEUP_PATH)

    result = build_audit(tenure_rows, lineup_rows)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("=" * 100)
    print("PBK POINT 14G V19 — VERIFIED TENURE -> IN-TENURE LINEUP AUDIT")
    print("=" * 100)

    for team in result["teams"]:
        dist = ", ".join(
            f"{item['formation']}={item['matches']}"
            for item in team["formation_distribution"]
        ) or "NONE"
        print(
            f"{team['team_id']} {team['team_name']} | "
            f"coach={team['verified_coach_name']} | "
            f"status={team['status']} | "
            f"fixtures={team['distinct_complete_fixtures']} | "
            f"formations={dist}"
        )

    print()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print("POINT14 IN-TENURE LINEUP AUDIT V19 PASSED")


if __name__ == "__main__":
    main()
