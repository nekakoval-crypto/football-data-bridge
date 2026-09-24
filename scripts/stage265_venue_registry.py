#!/usr/bin/env python3
"""PBK #265 — venue / stadium / crowd registry foundation.

Provider facts:
- team / venue identity
- nominal capacity
- surface
- address / city

PBK override facts are explicit, dated and evidence-backed.

This layer is descriptive/context-only. It grants no predictive,
betting, eligibility, value, stake or production authority.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.api_football_broker import api_get
    from scripts import standings_format_registry
except ModuleNotFoundError:
    from api_football_broker import api_get
    import standings_format_registry


ROOT = Path(__file__).resolve().parents[1]
OPS = Path(os.getenv("OPS_DIR", ROOT / "ops"))

OUTPUT = OPS / "pbk16_venue_registry.csv"
META = OPS / "stage265_venue_registry_last_run.json"
OVERRIDES = ROOT / "config" / "pbk_venue_overrides.csv"

SEASON = "2026"

PROJECTION_VERSION = "PBK_VENUE_REGISTRY_V1"

FIELDS = [
    "provider_league_id",
    "season",

    "team_id",
    "team_name",
    "team_country",

    "venue_id",
    "venue_name",
    "venue_address",
    "venue_city",

    "nominal_capacity",
    "surface_provider",

    "operational_capacity",
    "operational_capacity_status",

    "roof_type",
    "roof_state_default",

    "enclosure_class",
    "wind_exposure_class",
    "acoustic_enclosure_class",

    "pitch_orientation_deg",

    "attendance_actual_source_status",
    "attendance_expected_source_status",

    "crowd_demand_source_status",

    "override_valid_from",
    "override_valid_to",
    "override_evidence_status",
    "override_source",
    "override_notes",

    "context_only",
    "predictive_authority",
    "betting_authority",
    "projection_version",
]


def now_utc():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sval(value):
    return str(value or "").strip()


def positive_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return ""

    return number if number > 0 else ""


def read_csv(path):
    if not path.exists():
        return []

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temp.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    temp.replace(path)


def pbk16_league_ids():
    rows = []

    for (league_id, season), contract in (
        standings_format_registry
        .VERIFIED_FORMATS
        .items()
    ):
        if str(season) != SEASON:
            continue

        if contract.get("status") != "VERIFIED":
            continue

        rows.append(str(league_id))

    return sorted(
        set(rows),
        key=lambda value: int(value),
    )


def parse_date(value):
    text = sval(value)

    if not text:
        return None

    try:
        return datetime.strptime(
            text,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        return None


def active_override(
    rows,
    *,
    venue_id,
    team_id,
    as_of,
):
    candidates = []

    for row in rows:
        row_venue = sval(
            row.get("venue_id")
        )

        row_team = sval(
            row.get("team_id")
        )

        if row_venue and row_venue != venue_id:
            continue

        if row_team and row_team != team_id:
            continue

        if not row_venue and not row_team:
            continue

        valid_from = parse_date(
            row.get("valid_from")
        )

        valid_to = parse_date(
            row.get("valid_to")
        )

        if valid_from and as_of < valid_from:
            continue

        if valid_to and as_of > valid_to:
            continue

        candidates.append(row)

    if not candidates:
        return {}

    # Prefer most recently starting dated contract.
    candidates.sort(
        key=lambda row: (
            sval(row.get("valid_from")),
            sval(row.get("venue_id")),
            sval(row.get("team_id")),
        )
    )

    return candidates[-1]


def unknown_if_blank(value):
    value = sval(value)
    return value if value else "UNKNOWN"


def registry_row(
    *,
    league_id,
    response_row,
    override,
):
    team = (
        response_row.get("team")
        or {}
    )

    venue = (
        response_row.get("venue")
        or {}
    )

    nominal_capacity = positive_int(
        venue.get("capacity")
    )

    operational_capacity = positive_int(
        override.get(
            "operational_capacity"
        )
    )

    operational_status = (
        "VERIFIED_OVERRIDE"
        if operational_capacity
        else "NOMINAL_ONLY"
    )

    return {
        "provider_league_id": league_id,
        "season": SEASON,

        "team_id": sval(team.get("id")),
        "team_name": sval(team.get("name")),
        "team_country": sval(
            team.get("country")
        ),

        "venue_id": sval(
            venue.get("id")
        ),
        "venue_name": sval(
            venue.get("name")
        ),
        "venue_address": sval(
            venue.get("address")
        ),
        "venue_city": sval(
            venue.get("city")
        ),

        "nominal_capacity": nominal_capacity,
        "surface_provider": sval(
            venue.get("surface")
        ),

        "operational_capacity": (
            operational_capacity
        ),
        "operational_capacity_status": (
            operational_status
        ),

        "roof_type": unknown_if_blank(
            override.get("roof_type")
        ),
        "roof_state_default": (
            unknown_if_blank(
                override.get(
                    "roof_state_default"
                )
            )
        ),

        "enclosure_class": (
            unknown_if_blank(
                override.get(
                    "enclosure_class"
                )
            )
        ),
        "wind_exposure_class": (
            unknown_if_blank(
                override.get(
                    "wind_exposure_class"
                )
            )
        ),
        "acoustic_enclosure_class": (
            unknown_if_blank(
                override.get(
                    "acoustic_enclosure_class"
                )
            )
        ),

        "pitch_orientation_deg": sval(
            override.get(
                "pitch_orientation_deg"
            )
        ),

        # Not fabricated from capacity or match prestige.
        "attendance_actual_source_status":
            "NOT_CONNECTED",
        "attendance_expected_source_status":
            "NOT_CONNECTED",

        # Future research rail; never interpreted as attendance.
        "crowd_demand_source_status":
            "NOT_AUTHORIZED",

        "override_valid_from": sval(
            override.get("valid_from")
        ),
        "override_valid_to": sval(
            override.get("valid_to")
        ),
        "override_evidence_status": (
            unknown_if_blank(
                override.get(
                    "evidence_status"
                )
            )
        ),
        "override_source": sval(
            override.get("source")
        ),
        "override_notes": sval(
            override.get("notes")
        ),

        "context_only": "YES",
        "predictive_authority":
            "NOT_AUTHORIZED",
        "betting_authority":
            "NOT_AUTHORIZED",
        "projection_version":
            PROJECTION_VERSION,
    }


def main():
    run_at = datetime.now(
        timezone.utc
    )

    as_of = run_at.date()

    league_ids = pbk16_league_ids()
    override_rows = read_csv(
        OVERRIDES
    )

    rows = []
    provider_calls = 0
    warnings = []

    for league_id in league_ids:
        try:
            payload = api_get(
                "/teams",
                {
                    "league": league_id,
                    "season": SEASON,
                },
            )

            provider_calls += 1

            response = (
                payload.get("response")
                or []
            )

        except Exception as exc:
            warnings.append(
                f"league {league_id}: {exc}"
            )
            continue

        for item in response:
            team = item.get("team") or {}
            venue = item.get("venue") or {}

            team_id = sval(
                team.get("id")
            )

            venue_id = sval(
                venue.get("id")
            )

            override = active_override(
                override_rows,
                venue_id=venue_id,
                team_id=team_id,
                as_of=as_of,
            )

            rows.append(
                registry_row(
                    league_id=league_id,
                    response_row=item,
                    override=override,
                )
            )

    rows.sort(
        key=lambda row: (
            int(
                row[
                    "provider_league_id"
                ]
            ),
            row["team_name"],
        )
    )

    write_csv(
        OUTPUT,
        rows,
    )

    distinct_leagues = {
        row["provider_league_id"]
        for row in rows
    }

    distinct_venues = {
        row["venue_id"]
        for row in rows
        if row["venue_id"]
    }

    nominal_capacity_rows = sum(
        bool(row["nominal_capacity"])
        for row in rows
    )

    operational_override_rows = sum(
        row[
            "operational_capacity_status"
        ]
        == "VERIFIED_OVERRIDE"
        for row in rows
    )

    meta = {
        "version": PROJECTION_VERSION,
        "run_at_utc": now_utc(),
        "status": (
            "OK"
            if len(distinct_leagues)
            == len(league_ids)
            else "PARTIAL"
        ),
        "required_pbk16_leagues":
            len(league_ids),
        "captured_leagues":
            len(distinct_leagues),
        "team_venue_rows":
            len(rows),
        "distinct_venues":
            len(distinct_venues),
        "nominal_capacity_rows":
            nominal_capacity_rows,
        "operational_capacity_override_rows":
            operational_override_rows,
        "provider_calls":
            provider_calls,
        "warnings":
            warnings,
        "policy": {
            "nominal_capacity":
                "provider fact; never assumed to equal match-day usable capacity",
            "operational_capacity":
                "only explicit dated verified override",
            "attendance":
                "UNKNOWN/NOT_CONNECTED until evidence source exists",
            "crowd_demand":
                "research-only; never fabricated as attendance",
            "roof_wind_acoustics":
                "UNKNOWN until evidence-backed override exists",
            "authority":
                "context-only; no predictive/betting/value/stake authority",
        },
    }

    META.write_text(
        json.dumps(
            meta,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            meta,
            ensure_ascii=False,
        )
    )

    if len(distinct_leagues) != len(league_ids):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
