#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import os
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_football_broker import ApiFootballBroker


OPS = Path(os.getenv("OPS_DIR", "ops"))
ROSTERS = OPS / "team_rosters.csv"

OUT = OPS / "point14_v34_targeted_player_availability.csv"
META = OPS / "point14_v34_targeted_player_availability_last_run.json"

VERSION = "PBK_POINT14_V34_TARGETED_PLAYER_AVAILABILITY_V1"
SEASON = "2026"

# No fuzzy matching.
# Names are only aliases used to resolve an exact current-roster player_id.
TARGETS = [
    {
        "label": "Kylian Mbappe",
        "team_id": "541",
        "team_name": "Real Madrid",
        "kind": "WATCH",
        "aliases": ["Kylian Mbappe", "Kylian Mbappé", "K. Mbappe", "K. Mbappé"],
    },
    {
        "label": "Ibrahima Konate",
        "team_id": "541",
        "team_name": "Real Madrid",
        "kind": "WATCH",
        "aliases": ["Ibrahima Konate", "Ibrahima Konaté", "I. Konate", "I. Konaté"],
    },
    {
        "label": "Federico Valverde",
        "team_id": "541",
        "team_name": "Real Madrid",
        "kind": "WATCH",
        "aliases": ["Federico Valverde", "F. Valverde"],
    },
    {
        "label": "Joan Garcia",
        "team_id": "529",
        "team_name": "Barcelona",
        "kind": "WATCH_POSITIVE",
        "aliases": ["Joan Garcia", "Joan García", "J. Garcia", "J. García"],
    },

    # Positive controls from the V34.2 season injury ledger.
    {
        "label": "Eder Militao",
        "team_id": "541",
        "team_name": "Real Madrid",
        "kind": "POSITIVE_CONTROL",
        "aliases": ["Eder Militao", "Éder Militão", "E. Militao", "E. Militão"],
    },
    {
        "label": "Frenkie de Jong",
        "team_id": "529",
        "team_name": "Barcelona",
        "kind": "POSITIVE_CONTROL",
        "aliases": ["Frenkie de Jong", "F. de Jong"],
    },
    {
        "label": "Dejan Kulusevski",
        "team_id": "47",
        "team_name": "Tottenham",
        "kind": "POSITIVE_CONTROL",
        "aliases": ["Dejan Kulusevski", "D. Kulusevski"],
    },
]


FIELDS = [
    "kind",
    "label",
    "team_id",
    "team_name",
    "player_id",
    "roster_player_name",
    "roster_captured_at_utc",
    "player_endpoint_name",
    "player_injured",
    "player_endpoint_rows",
    "sidelined_rows",
    "latest_sidelined_type",
    "latest_sidelined_start",
    "latest_sidelined_end",
    "latest_sidelined_open",
    "captured_at_utc",
]


def now_iso():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def norm(value):
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        ch for ch in text
        if not unicodedata.combining(ch)
    )
    return " ".join(text.split())


def read_csv(path):
    if not path.exists():
        return []

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


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


def latest_roster_rows(rows, team_id):
    team_rows = [
        row for row in rows
        if str(row.get("team_id") or "").strip() == str(team_id)
    ]

    if not team_rows:
        return []

    stamps = [
        str(row.get("captured_at_utc") or "").strip()
        for row in team_rows
        if str(row.get("captured_at_utc") or "").strip()
    ]

    if not stamps:
        return team_rows

    latest = max(stamps)

    return [
        row for row in team_rows
        if str(row.get("captured_at_utc") or "").strip() == latest
    ]


def resolve_player(target, roster_rows):
    rows = latest_roster_rows(
        roster_rows,
        target["team_id"],
    )

    aliases = {
        norm(alias)
        for alias in target["aliases"]
    }

    matches = [
        row for row in rows
        if norm(row.get("player_name")) in aliases
    ]

    if len(matches) == 1:
        return {
            "status": "EXACT_ALIAS_MATCH",
            "row": matches[0],
        }

    if not matches:
        return {
            "status": "NO_EXACT_ALIAS_MATCH",
            "row": None,
            "available_names": sorted(
                str(row.get("player_name") or "")
                for row in rows
            ),
        }

    return {
        "status": "AMBIGUOUS_EXACT_ALIAS_MATCH",
        "row": None,
        "matches": [
            {
                "player_id": row.get("player_id"),
                "player_name": row.get("player_name"),
            }
            for row in matches
        ],
    }


def parse_date(value):
    value = str(value or "").strip()

    if not value or value.lower() == "unknown":
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        try:
            return datetime.strptime(
                value[:10],
                "%Y-%m-%d",
            ).replace(tzinfo=timezone.utc)
        except Exception:
            return None


def latest_sidelined(response):
    if not response:
        return None

    def key(item):
        return (
            parse_date(item.get("start"))
            or datetime.min.replace(tzinfo=timezone.utc)
        )

    return max(
        response,
        key=key,
    )


def sidelined_open(item):
    if not item:
        return False

    end = str(item.get("end") or "").strip()

    return (
        not end
        or end.lower() == "unknown"
    )


def main():
    roster_rows = read_csv(ROSTERS)

    broker = ApiFootballBroker(
        max_real_calls=20,
        default_ttl_seconds=4 * 3600,
    )

    captured = now_iso()

    results = []
    resolution_report = []

    for target in TARGETS:
        resolution = resolve_player(
            target,
            roster_rows,
        )

        resolution_report.append({
            "label": target["label"],
            "team_id": target["team_id"],
            "team_name": target["team_name"],
            "kind": target["kind"],
            "resolution_status": resolution["status"],
            "resolved_player_id": (
                str(
                    (resolution.get("row") or {})
                    .get("player_id") or ""
                )
            ),
            "resolved_player_name": (
                str(
                    (resolution.get("row") or {})
                    .get("player_name") or ""
                )
            ),
        })

        if resolution["status"] != "EXACT_ALIAS_MATCH":
            continue

        roster = resolution["row"]

        player_id = str(
            roster.get("player_id") or ""
        ).strip()

        # Volatile current-state evidence:
        # force real provider refresh rather than trusting an old R2 payload.
        player_payload = broker.get(
            "/players",
            {
                "id": player_id,
                "season": SEASON,
            },
            force_refresh=True,
            archive_first=False,
            ttl_seconds=4 * 3600,
        )

        player_response = (
            player_payload.get("response")
            or []
        )

        player_profile = {}

        if player_response:
            player_profile = (
                player_response[0].get("player")
                or {}
            )

        injured = player_profile.get("injured")

        # History/current episode context.
        sidelined_payload = broker.get(
            "/sidelined",
            {
                "player": player_id,
            },
            force_refresh=True,
            archive_first=False,
            ttl_seconds=12 * 3600,
        )

        sidelined_response = (
            sidelined_payload.get("response")
            or []
        )

        latest = latest_sidelined(
            sidelined_response
        )

        results.append({
            "kind": target["kind"],
            "label": target["label"],
            "team_id": target["team_id"],
            "team_name": target["team_name"],
            "player_id": player_id,
            "roster_player_name": str(
                roster.get("player_name")
                or ""
            ),
            "roster_captured_at_utc": str(
                roster.get("captured_at_utc")
                or ""
            ),
            "player_endpoint_name": str(
                player_profile.get("name")
                or ""
            ),
            "player_injured": (
                str(injured).upper()
                if isinstance(injured, bool)
                else "UNKNOWN"
            ),
            "player_endpoint_rows": len(
                player_response
            ),
            "sidelined_rows": len(
                sidelined_response
            ),
            "latest_sidelined_type": (
                str(
                    (latest or {}).get("type")
                    or ""
                )
            ),
            "latest_sidelined_start": (
                str(
                    (latest or {}).get("start")
                    or ""
                )
            ),
            "latest_sidelined_end": (
                str(
                    (latest or {}).get("end")
                    or ""
                )
            ),
            "latest_sidelined_open": (
                "YES"
                if sidelined_open(latest)
                else "NO"
            ),
            "captured_at_utc": captured,
        })

    write_csv(
        OUT,
        results,
    )

    report = {
        "version": VERSION,
        "run_at_utc": captured,
        "season": SEASON,
        "target_count": len(TARGETS),
        "resolved_count": len(results),
        "resolution_report": resolution_report,
        "results": results,
        "broker_stats": broker.stats(),

        "provider_contract": {
            "players_injured": (
                "LIGHTWEIGHT_CURRENT_AVAILABILITY_FLAG"
            ),
            "sidelined": (
                "PLAYER_INJURY_SUSPENSION_HISTORY"
            ),
            "fixture_injuries": (
                "LATE_MATCH_SPECIFIC_EVIDENCE"
            ),
        },

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
    print("=" * 118)
    print("TARGETED CURRENT PLAYER AVAILABILITY")
    print("=" * 118)

    for row in results:
        print(
            f"{row['kind']:<18} "
            f"{row['team_name']:<16} "
            f"{row['roster_player_name']:<24} "
            f"id={row['player_id']:<8} "
            f"injured={row['player_injured']:<7} "
            f"latest={row['latest_sidelined_type']:<25} "
            f"{row['latest_sidelined_start']:<12} "
            f"-> {row['latest_sidelined_end']}"
        )

    unresolved = [
        item for item in resolution_report
        if item["resolution_status"] != "EXACT_ALIAS_MATCH"
    ]

    if unresolved:
        print()
        print("=" * 118)
        print("UNRESOLVED ROSTER IDENTITIES")
        print("=" * 118)

        for item in unresolved:
            print(
                item["label"],
                "|",
                item["team_name"],
                "|",
                item["resolution_status"],
            )


if __name__ == "__main__":
    main()
