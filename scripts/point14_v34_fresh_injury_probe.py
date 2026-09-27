#!/usr/bin/env python3

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_football_broker import ApiFootballBroker

OPS = Path(os.getenv("OPS_DIR", "ops"))

OUT = OPS / "point14_v34_fresh_injury_probe.csv"
META = OPS / "point14_v34_fresh_injury_probe_last_run.json"

VERSION = "PBK_POINT14_V34_FRESH_INJURY_PROBE_V1"

FIXTURES = [
    {
        "fixture_id": "1557425",
        "league_id": "39",
        "season": "2026",
        "match": "Manchester United - Tottenham",
    },
    {
        "fixture_id": "1557424",
        "league_id": "39",
        "season": "2026",
        "match": "Liverpool - Manchester City",
    },
    {
        "fixture_id": "1557417",
        "league_id": "39",
        "season": "2026",
        "match": "Arsenal - Leeds",
    },
    {
        "fixture_id": "1570404",
        "league_id": "140",
        "season": "2026",
        "match": "Barcelona - Getafe",
    },
    {
        "fixture_id": "1570411",
        "league_id": "140",
        "season": "2026",
        "match": "Real Madrid - Villarreal",
    },
    {
        "fixture_id": "1550139",
        "league_id": "135",
        "season": "2026",
        "match": "Como - AS Roma",
    },
    {
        "fixture_id": "1550141",
        "league_id": "135",
        "season": "2026",
        "match": "Inter - Parma",
    },
]

FIELDS = [
    "fixture_id",
    "match",
    "league_id",
    "coverage_injuries",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "type",
    "reason",
    "provider_fixture_id",
    "captured_at_utc",
]


def now_iso():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def coverage_from_payload(payload):
    response = payload.get("response") or []

    if not response:
        return None

    coverage = (
        response[0]
        .get("seasons", [{}])[-1]
        .get("coverage", {})
    )

    value = coverage.get("injuries")

    if isinstance(value, bool):
        return value

    return None


def normalize_injury(item, fixture, captured):
    player = item.get("player") or {}
    team = item.get("team") or {}
    fixture_obj = item.get("fixture") or {}

    return {
        "fixture_id": fixture["fixture_id"],
        "match": fixture["match"],
        "league_id": fixture["league_id"],
        "coverage_injuries": "YES",
        "team_id": str(team.get("id") or ""),
        "team_name": str(team.get("name") or ""),
        "player_id": str(player.get("id") or ""),
        "player_name": str(player.get("name") or ""),
        "type": str(player.get("type") or item.get("type") or ""),
        "reason": str(player.get("reason") or item.get("reason") or ""),
        "provider_fixture_id": str(
            fixture_obj.get("id")
            or fixture["fixture_id"]
        ),
        "captured_at_utc": captured,
    }


def main():
    broker = ApiFootballBroker(
        max_real_calls=20,
        default_ttl_seconds=4 * 3600,
    )

    captured = now_iso()

    coverage_cache = {}
    rows = []
    fixture_results = []

    for fixture in FIXTURES:
        league_key = (
            fixture["league_id"],
            fixture["season"],
        )

        if league_key not in coverage_cache:
            payload = broker.get(
                "/leagues",
                {
                    "id": fixture["league_id"],
                    "season": fixture["season"],
                },
                ttl_seconds=24 * 3600,
                archive_first=True,
                force_refresh=False,
            )

            coverage_cache[league_key] = (
                coverage_from_payload(payload)
            )

        coverage = coverage_cache[league_key]

        if coverage is not True:
            fixture_results.append({
                "fixture_id": fixture["fixture_id"],
                "match": fixture["match"],
                "coverage_injuries": coverage,
                "result": "COVERAGE_NOT_CONFIRMED",
                "response_rows": 0,
            })

            rows.append({
                "fixture_id": fixture["fixture_id"],
                "match": fixture["match"],
                "league_id": fixture["league_id"],
                "coverage_injuries": (
                    "NO" if coverage is False else "UNKNOWN"
                ),
                "captured_at_utc": captured,
            })

            continue

        payload = broker.get(
            "/injuries",
            {
                "fixture": fixture["fixture_id"],
            },
            ttl_seconds=4 * 3600,
            archive_first=True,
            force_refresh=False,
        )

        response = payload.get("response") or []

        fixture_results.append({
            "fixture_id": fixture["fixture_id"],
            "match": fixture["match"],
            "coverage_injuries": True,
            "result": (
                "CAPTURED"
                if response
                else "EMPTY"
            ),
            "response_rows": len(response),
        })

        if not response:
            rows.append({
                "fixture_id": fixture["fixture_id"],
                "match": fixture["match"],
                "league_id": fixture["league_id"],
                "coverage_injuries": "YES",
                "captured_at_utc": captured,
            })

        for item in response:
            rows.append(
                normalize_injury(
                    item,
                    fixture,
                    captured,
                )
            )

    write_csv(OUT, rows)

    stats = broker.stats()

    report = {
        "version": VERSION,
        "run_at_utc": captured,
        "fixture_count": len(FIXTURES),
        "league_coverage_checks": len(coverage_cache),
        "coverage": {
            f"{league}:{season}": value
            for (league, season), value
            in coverage_cache.items()
        },
        "fixture_results": fixture_results,
        "normalized_rows": len([
            row for row in rows
            if row.get("player_id")
        ]),
        "broker_stats": stats,
        "archive_first": True,
        "injury_ttl_seconds": 14400,
        "research_only": True,
        "probability_status": "UNCALIBRATED",
        "operational_betting_authority": False,
        "mutates_probable_xi": False,
    }

    META.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("=" * 100)
    print("FRESH INJURY / SUSPENSION ROWS")
    print("=" * 100)

    injury_rows = [
        row for row in rows
        if row.get("player_id")
    ]

    if not injury_rows:
        print("NO INJURY ROWS RETURNED")

    for row in injury_rows:
        print(
            f"{row['match']:<38} "
            f"{row['team_name']:<22} "
            f"{row['player_name']:<28} "
            f"{row['type']:<12} "
            f"{row['reason']}"
        )


if __name__ == "__main__":
    main()
