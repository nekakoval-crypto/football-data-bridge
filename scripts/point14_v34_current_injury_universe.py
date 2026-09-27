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

OUT = OPS / "point14_v34_current_injury_universe.csv"
META = OPS / "point14_v34_current_injury_universe_last_run.json"

VERSION = "PBK_POINT14_V34_CURRENT_INJURY_UNIVERSE_V1"

LEAGUES = [
    ("39", "2026", "Premier League"),
    ("140", "2026", "La Liga"),
    ("135", "2026", "Serie A"),
]

TARGET_TEAMS = {
    "33": "Manchester United",
    "47": "Tottenham",
    "40": "Liverpool",
    "50": "Manchester City",
    "42": "Arsenal",
    "63": "Leeds",
    "529": "Barcelona",
    "546": "Getafe",
    "541": "Real Madrid",
    "533": "Villarreal",
    "895": "Como",
    "497": "AS Roma",
    "505": "Inter",
    "523": "Parma",
}

WATCH_NAMES = {
    "kylian mbappé",
    "kylian mbappe",
    "i. konaté",
    "i. konate",
    "f. valverde",
    "federico valverde",
    "joan garcía",
    "joan garcia",
}

FIELDS = [
    "league_id",
    "league_name",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "type",
    "reason",
    "fixture_id",
    "fixture_date",
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


def normalize(item, league_id, league_name, captured):
    player = item.get("player") or {}
    team = item.get("team") or {}
    fixture = item.get("fixture") or {}

    return {
        "league_id": league_id,
        "league_name": league_name,
        "team_id": str(team.get("id") or ""),
        "team_name": str(team.get("name") or ""),
        "player_id": str(player.get("id") or ""),
        "player_name": str(player.get("name") or ""),
        "type": str(
            player.get("type")
            or item.get("type")
            or ""
        ),
        "reason": str(
            player.get("reason")
            or item.get("reason")
            or ""
        ),
        "fixture_id": str(fixture.get("id") or ""),
        "fixture_date": str(fixture.get("date") or ""),
        "captured_at_utc": captured,
    }


def main():
    broker = ApiFootballBroker(
        max_real_calls=6,
        default_ttl_seconds=4 * 3600,
    )

    captured = now_iso()

    all_rows = []
    league_results = []

    for league_id, season, league_name in LEAGUES:

        # IMPORTANT:
        # Current injuries are volatile.
        # Force a true provider refresh for this diagnostic.
        payload = broker.get(
            "/injuries",
            {
                "league": league_id,
                "season": season,
            },
            ttl_seconds=4 * 3600,
            archive_first=False,
            force_refresh=True,
        )

        response = payload.get("response") or []
        paging = payload.get("paging") or {}

        league_results.append({
            "league_id": league_id,
            "league_name": league_name,
            "response_rows": len(response),
            "paging_current": paging.get("current"),
            "paging_total": paging.get("total"),
        })

        for item in response:
            all_rows.append(
                normalize(
                    item,
                    league_id,
                    league_name,
                    captured,
                )
            )

    target_rows = [
        row
        for row in all_rows
        if row["team_id"] in TARGET_TEAMS
    ]

    write_csv(
        OUT,
        target_rows,
    )

    watch_hits = [
        row for row in target_rows
        if row["player_name"].strip().lower()
        in WATCH_NAMES
    ]

    team_counts = {}

    for row in target_rows:
        key = (
            row["team_id"],
            row["team_name"],
        )

        team_counts[key] = (
            team_counts.get(key, 0) + 1
        )

    report = {
        "version": VERSION,
        "run_at_utc": captured,
        "league_results": league_results,
        "provider_rows_total": len(all_rows),
        "target_team_rows": len(target_rows),
        "watch_hits": watch_hits,
        "team_counts": [
            {
                "team_id": team_id,
                "team_name": team_name,
                "injury_rows": count,
            }
            for (
                team_id,
                team_name,
            ), count
            in sorted(team_counts.items())
        ],
        "broker_stats": broker.stats(),
        "force_provider_refresh": True,
        "archive_used_as_fresh_source": False,
        "archive_write_expected": True,
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
    print("=" * 110)
    print("TARGET CLUB CURRENT INJURIES / SUSPENSIONS")
    print("=" * 110)

    if not target_rows:
        print("NO TARGET-TEAM ROWS")

    for row in target_rows:
        print(
            f"{row['league_name']:<16} "
            f"{row['team_name']:<22} "
            f"{row['player_name']:<28} "
            f"{row['type']:<12} "
            f"{row['reason']:<28} "
            f"fixture={row['fixture_id']}"
        )

    print()
    print("=" * 110)
    print("WATCH PLAYERS")
    print("=" * 110)

    if not watch_hits:
        print("NO WATCH-PLAYER HITS")

    for row in watch_hits:
        print(
            row["team_name"],
            "|",
            row["player_name"],
            "|",
            row["type"],
            "|",
            row["reason"],
            "| fixture=",
            row["fixture_id"],
        )


if __name__ == "__main__":
    main()
