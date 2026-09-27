#!/usr/bin/env python3
"""PBK Point14 V30.1 — R2 archive-only current-season lineup audit.

Safety:
- reads fixture inventory from the rolling current-season archive;
- reads exact /fixtures/lineups payloads from durable R2 evidence only;
- never calls API-Football;
- never requires API_FOOTBALL_KEY;
- never mutates probabilities, eligibility, stakes or Forward Journal.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import stage80_current_season_lineup_backfill as current
from api_football_broker import request_key
from api_football_raw_archive import (
    read_archived_response,
    s3_config_from_env,
)

OPS = current.OPS
META = OPS / "point14_v30_r2_lineup_archive_audit.json"

VERSION = "PBK_POINT14_V30_R2_LINEUP_ARCHIVE_AUDIT_V1"


def main():
    config = s3_config_from_env()

    if config is None:
        raise RuntimeError(
            "R2 raw archive is not configured in this environment"
        )

    source_rows = current.base.read_csv(current.SOURCE)
    history = current.rolling_terminal_fixture_map(source_rows)
    season = current.current_season_number(history)

    fixtures = {
        fixture_id: row
        for fixture_id, row in history.items()
        if current.base.season_number(row) == season
    }

    ordered = sorted(
        fixtures.items(),
        key=lambda item: (
            item[1].get("kickoff_utc", ""),
            item[0],
        ),
        reverse=True,
    )

    hits = []
    misses = []
    errors = []

    for fixture_id, fixture in ordered:
        key = request_key(
            "GET",
            "/fixtures/lineups",
            {"fixture": fixture_id},
        )

        try:
            payload = read_archived_response(key)
        except Exception as exc:
            errors.append({
                "fixture_id": fixture_id,
                "country": fixture.get("country", ""),
                "kickoff_utc": fixture.get("kickoff_utc", ""),
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        if payload is None:
            misses.append({
                "fixture_id": fixture_id,
                "country": fixture.get("country", ""),
                "kickoff_utc": fixture.get("kickoff_utc", ""),
                "home_team": fixture.get("home_team", ""),
                "away_team": fixture.get("away_team", ""),
            })
            continue

        response = payload.get("response")

        if not isinstance(response, list):
            errors.append({
                "fixture_id": fixture_id,
                "country": fixture.get("country", ""),
                "kickoff_utc": fixture.get("kickoff_utc", ""),
                "error": "ARCHIVED_PAYLOAD_RESPONSE_NOT_LIST",
            })
            continue

        hits.append({
            "fixture_id": fixture_id,
            "country": fixture.get("country", ""),
            "kickoff_utc": fixture.get("kickoff_utc", ""),
            "home_team": fixture.get("home_team", ""),
            "away_team": fixture.get("away_team", ""),
            "response_rows": len(response),
        })

    nonempty = [
        row for row in hits
        if row["response_rows"] > 0
    ]

    empty = [
        row for row in hits
        if row["response_rows"] == 0
    ]

    hit_by_country = Counter(
        row["country"] for row in hits
    )

    miss_by_country = Counter(
        row["country"] for row in misses
    )

    meta = {
        "version": VERSION,
        "status": "OK" if not errors else "ATTENTION",
        "season": season,
        "source_path": str(current.SOURCE).replace("\\", "/"),
        "terminal_fixtures": len(fixtures),
        "archive_hits": len(hits),
        "archive_hits_with_lineup_data": len(nonempty),
        "archive_hits_empty_response": len(empty),
        "archive_misses": len(misses),
        "archive_errors": len(errors),
        "provider_calls": 0,
        "api_football_key_required": False,
        "archive_only": True,
        "calls_avoided_by_archive_hit": len(hits),
        "calls_still_potentially_needed": len(misses) + len(errors),
        "hit_by_country": dict(sorted(hit_by_country.items())),
        "miss_by_country": dict(sorted(miss_by_country.items())),
        "latest_archive_hits": hits[:20],
        "latest_archive_misses": misses[:20],
        "errors": errors[:20],
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }

    META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(meta, ensure_ascii=False, indent=2))

    if season != 2026:
        raise SystemExit(
            f"expected current season 2026, got {season}"
        )

    if len(hits) + len(misses) + len(errors) != len(fixtures):
        raise SystemExit(
            "fixture accounting mismatch"
        )

    print("POINT14 V30.1 R2 ARCHIVE-ONLY AUDIT PASSED")


if __name__ == "__main__":
    main()
