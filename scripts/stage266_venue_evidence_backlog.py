#!/usr/bin/env python3
"""PBK #266 — deterministic venue evidence backlog.

Consumes the provider-backed PBK16 venue registry and creates one evidence
task per missing stadium/environment attribute.

Important:
- zero provider calls;
- zero web calls;
- no roof/wind/acoustic/orientation inference;
- task priority is only collection priority;
- no predictive/betting/value/stake authority.
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


OPS = Path(os.getenv("OPS_DIR", "ops"))

REGISTRY = OPS / "pbk16_venue_registry.csv"
BACKLOG = OPS / "venue_evidence_backlog.csv"
META = OPS / "stage266_venue_evidence_backlog_last_run.json"

VERSION = "PBK_VENUE_EVIDENCE_BACKLOG_V1"

EVIDENCE_FIELDS = {
    "operational_capacity": {
        "temporality": "DATED_OR_CURRENT",
        "evidence_required": "DIRECT_OR_AUTHORITATIVE",
    },
    "roof_type": {
        "temporality": "STRUCTURAL_WITH_EFFECTIVE_DATES_IF_CHANGED",
        "evidence_required": "DIRECT_OR_AUTHORITATIVE",
    },
    "roof_state_default": {
        "temporality": "STRUCTURAL_OR_MATCH_SPECIFIC",
        "evidence_required": "DIRECT_OR_AUTHORITATIVE",
    },
    "enclosure_class": {
        "temporality": "STRUCTURAL",
        "evidence_required": "EVIDENCE_BACKED_CLASSIFICATION",
    },
    "wind_exposure_class": {
        "temporality": "STRUCTURAL",
        "evidence_required": "EVIDENCE_BACKED_CLASSIFICATION",
    },
    "acoustic_enclosure_class": {
        "temporality": "STRUCTURAL",
        "evidence_required": "EVIDENCE_BACKED_CLASSIFICATION",
    },
    "pitch_orientation_deg": {
        "temporality": "STRUCTURAL",
        "evidence_required": "DIRECT_GEOMETRY_OR_VERIFIED_MAP",
    },
}

FIELDS = [
    "venue_id",
    "venue_name",
    "venue_city",

    "team_count",
    "team_names",
    "league_ids",
    "shared_venue",

    "nominal_capacity",
    "surface_provider",

    "evidence_field",
    "current_value",

    "capture_priority",
    "priority_reason",

    "evidence_temporality",
    "evidence_required",

    "backlog_status",
    "first_queued_at_utc",
    "last_seen_at_utc",

    "evidence_status",
    "source",
    "source_checked_at_utc",
    "effective_from",
    "effective_to",
    "captured_value",
    "notes",

    "provider_calls",
    "web_calls",

    "inference_allowed",
    "research_only",
    "operational_betting_authority",
    "creates_signal",
    "probability_mutation",
    "eligibility_mutation",
    "stake_changes",
    "forward_journal_mutation",
]


def now_iso(now=None):
    now = now or datetime.now(timezone.utc)

    return (
        now.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sval(row, key):
    return str(
        (row or {}).get(key) or ""
    ).strip()


def read_csv(path):
    path = Path(path)

    if not path.exists():
        return []

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        return list(
            csv.DictReader(stream)
        )


def write_csv(path, rows):
    path = Path(path)

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


def write_json(path, payload):
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    temp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temp.replace(path)


def int_or_zero(value):
    try:
        return int(
            str(value or "").strip()
        )
    except (TypeError, ValueError):
        return 0


def missing_value(value):
    return str(
        value or ""
    ).strip() in {
        "",
        "UNKNOWN",
        "NOT_CONNECTED",
        "NOT_AUTHORIZED",
    }


def venue_priority(
    *,
    nominal_capacity,
    team_count,
    surface,
):
    """Research collection priority only.

    This must never be interpreted as football significance.
    """
    capacity = int_or_zero(
        nominal_capacity
    )

    reasons = []
    score = 100

    if team_count > 1:
        score -= 30
        reasons.append(
            "SHARED_VENUE"
        )

    if capacity >= 50000:
        score -= 25
        reasons.append(
            "CAPACITY_GE_50000"
        )
    elif capacity >= 30000:
        score -= 15
        reasons.append(
            "CAPACITY_GE_30000"
        )
    elif capacity >= 15000:
        score -= 5
        reasons.append(
            "CAPACITY_GE_15000"
        )

    if (
        str(surface or "")
        .strip()
        .lower()
        != "grass"
    ):
        score -= 10
        reasons.append(
            "NON_GRASS_SURFACE"
        )

    score = max(
        1,
        score,
    )

    return (
        score,
        "|".join(reasons)
        or "STANDARD_QUEUE",
    )


def aggregate_venues(rows):
    venues = {}

    for row in rows:
        venue_id = sval(
            row,
            "venue_id",
        )

        if not venue_id:
            raise ValueError(
                "registry row missing venue_id"
            )

        item = venues.setdefault(
            venue_id,
            {
                "venue_id": venue_id,
                "venue_name": sval(
                    row,
                    "venue_name",
                ),
                "venue_city": sval(
                    row,
                    "venue_city",
                ),
                "nominal_capacity":
                    sval(
                        row,
                        "nominal_capacity",
                    ),
                "surface_provider":
                    sval(
                        row,
                        "surface_provider",
                    ),
                "teams": set(),
                "league_ids": set(),
                "rows": [],
            },
        )

        # Provider identity for one venue ID must be stable.
        for key in (
            "venue_name",
            "venue_city",
            "nominal_capacity",
            "surface_provider",
        ):
            incoming = sval(
                row,
                key,
            )

            existing = str(
                item[key] or ""
            ).strip()

            if (
                incoming
                and existing
                and incoming != existing
            ):
                raise ValueError(
                    "inconsistent venue identity "
                    f"{venue_id} field={key}: "
                    f"{existing!r} != {incoming!r}"
                )

            if incoming:
                item[key] = incoming

        team_name = sval(
            row,
            "team_name",
        )

        if team_name:
            item["teams"].add(
                team_name
            )

        league_id = sval(
            row,
            "provider_league_id",
        )

        if league_id:
            item[
                "league_ids"
            ].add(
                league_id
            )

        item["rows"].append(
            row
        )

    return venues


def aggregate_current_value(
    venue,
    field,
):
    values = {
        sval(row, field)
        for row in venue["rows"]
        if not missing_value(
            row.get(field)
        )
    }

    if len(values) > 1:
        raise ValueError(
            f"inconsistent {field} "
            f"for venue {venue['venue_id']}: "
            f"{sorted(values)}"
        )

    if not values:
        return ""

    return next(iter(values))


def build_backlog(
    registry_rows,
    existing_rows,
    now=None,
):
    now_value = now_iso(now)

    venues = aggregate_venues(
        registry_rows
    )

    existing = {
        (
            sval(row, "venue_id"),
            sval(row, "evidence_field"),
        ): dict(row)
        for row in existing_rows
        if (
            sval(row, "venue_id")
            and sval(
                row,
                "evidence_field",
            )
        )
    }

    tasks = []

    for venue_id, venue in venues.items():
        team_count = len(
            venue["teams"]
        )

        priority, reason = (
            venue_priority(
                nominal_capacity=venue[
                    "nominal_capacity"
                ],
                team_count=team_count,
                surface=venue[
                    "surface_provider"
                ],
            )
        )

        for field, contract in (
            EVIDENCE_FIELDS.items()
        ):
            current = (
                aggregate_current_value(
                    venue,
                    field,
                )
            )

            # Evidence already present in the canonical registry:
            # no backlog task is needed.
            if not missing_value(
                current
            ):
                continue

            old = existing.get(
                (
                    venue_id,
                    field,
                ),
                {},
            )

            status = sval(
                old,
                "backlog_status",
            )

            if status not in {
                "PENDING",
                "CAPTURED",
                "NO_DATA",
                "NEEDS_REVIEW",
                "ERROR",
            }:
                status = "PENDING"

            tasks.append({
                "venue_id": venue_id,
                "venue_name":
                    venue["venue_name"],
                "venue_city":
                    venue["venue_city"],

                "team_count":
                    str(team_count),
                "team_names":
                    " | ".join(
                        sorted(
                            venue["teams"]
                        )
                    ),
                "league_ids":
                    " | ".join(
                        sorted(
                            venue[
                                "league_ids"
                            ],
                            key=int,
                        )
                    ),
                "shared_venue": (
                    "true"
                    if team_count > 1
                    else "false"
                ),

                "nominal_capacity":
                    venue[
                        "nominal_capacity"
                    ],
                "surface_provider":
                    venue[
                        "surface_provider"
                    ],

                "evidence_field":
                    field,
                "current_value": "",

                "capture_priority":
                    str(priority),
                "priority_reason":
                    reason,

                "evidence_temporality":
                    contract[
                        "temporality"
                    ],
                "evidence_required":
                    contract[
                        "evidence_required"
                    ],

                "backlog_status":
                    status,
                "first_queued_at_utc":
                    sval(
                        old,
                        "first_queued_at_utc",
                    )
                    or now_value,
                "last_seen_at_utc":
                    now_value,

                "evidence_status":
                    sval(
                        old,
                        "evidence_status",
                    ),
                "source":
                    sval(
                        old,
                        "source",
                    ),
                "source_checked_at_utc":
                    sval(
                        old,
                        "source_checked_at_utc",
                    ),
                "effective_from":
                    sval(
                        old,
                        "effective_from",
                    ),
                "effective_to":
                    sval(
                        old,
                        "effective_to",
                    ),
                "captured_value":
                    sval(
                        old,
                        "captured_value",
                    ),
                "notes":
                    sval(
                        old,
                        "notes",
                    ),

                "provider_calls": "0",
                "web_calls": "0",

                "inference_allowed":
                    "false",
                "research_only":
                    "true",
                "operational_betting_authority":
                    "false",
                "creates_signal":
                    "false",
                "probability_mutation":
                    "false",
                "eligibility_mutation":
                    "false",
                "stake_changes":
                    "false",
                "forward_journal_mutation":
                    "false",
            })

    tasks.sort(
        key=lambda row: (
            int(
                row[
                    "capture_priority"
                ]
            ),
            -int_or_zero(
                row[
                    "nominal_capacity"
                ]
            ),
            row["venue_name"],
            row["evidence_field"],
        )
    )

    return tasks, venues


def run(
    registry_path=REGISTRY,
    backlog_path=BACKLOG,
    meta_path=META,
    now=None,
):
    registry_rows = read_csv(
        registry_path
    )

    if not registry_rows:
        raise ValueError(
            "PBK16 venue registry missing or empty"
        )

    if len(registry_rows) != 258:
        raise ValueError(
            "unexpected venue-registry row count: "
            f"{len(registry_rows)}"
        )

    league_ids = {
        sval(
            row,
            "provider_league_id",
        )
        for row in registry_rows
        if sval(
            row,
            "provider_league_id",
        )
    }

    if len(league_ids) != 16:
        raise ValueError(
            "venue registry is not PBK16 complete"
        )

    if not all(
        sval(
            row,
            "context_only",
        )
        == "YES"
        and sval(
            row,
            "predictive_authority",
        )
        == "NOT_AUTHORIZED"
        and sval(
            row,
            "betting_authority",
        )
        == "NOT_AUTHORIZED"
        for row in registry_rows
    ):
        raise ValueError(
            "venue registry authority contract invalid"
        )

    existing_rows = read_csv(
        backlog_path
    )

    tasks, venues = build_backlog(
        registry_rows,
        existing_rows,
        now=now,
    )

    duplicate_keys = (
        len(tasks)
        - len({
            (
                row["venue_id"],
                row["evidence_field"],
            )
            for row in tasks
        })
    )

    if duplicate_keys:
        raise ValueError(
            "duplicate venue evidence tasks: "
            f"{duplicate_keys}"
        )

    expected_fields = set(
        EVIDENCE_FIELDS
    )

    invalid_rows = sum(
        not (
            row["venue_id"]
            and row[
                "evidence_field"
            ] in expected_fields
            and row[
                "inference_allowed"
            ] == "false"
            and row[
                "research_only"
            ] == "true"
            and row[
                "operational_betting_authority"
            ] == "false"
            and row[
                "creates_signal"
            ] == "false"
            and row[
                "probability_mutation"
            ] == "false"
            and row[
                "eligibility_mutation"
            ] == "false"
            and row[
                "stake_changes"
            ] == "false"
            and row[
                "forward_journal_mutation"
            ] == "false"
            and row[
                "provider_calls"
            ] == "0"
            and row[
                "web_calls"
            ] == "0"
        )
        for row in tasks
    )

    field_counts = Counter(
        row["evidence_field"]
        for row in tasks
    )

    priority_counts = Counter(
        row["capture_priority"]
        for row in tasks
    )

    shared_venues = sum(
        len(venue["teams"]) > 1
        for venue in venues.values()
    )

    artificial_venues = sum(
        str(
            venue[
                "surface_provider"
            ]
            or ""
        )
        .strip()
        .lower()
        != "grass"
        for venue in venues.values()
    )

    status = (
        "OK"
        if (
            len(venues) == 252
            and duplicate_keys == 0
            and invalid_rows == 0
            and tasks
        )
        else "ATTENTION"
    )

    meta = {
        "version": VERSION,
        "generated_at_utc":
            now_iso(now),
        "status": status,

        "source_registry_rows":
            len(registry_rows),
        "pbk16_leagues":
            len(league_ids),
        "unique_venues":
            len(venues),

        "shared_venues":
            shared_venues,
        "non_grass_venues":
            artificial_venues,

        "evidence_fields":
            sorted(
                EVIDENCE_FIELDS
            ),
        "evidence_field_count":
            len(EVIDENCE_FIELDS),

        "backlog_rows":
            len(tasks),
        "field_counts":
            dict(
                sorted(
                    field_counts.items()
                )
            ),
        "priority_counts":
            dict(
                sorted(
                    priority_counts.items(),
                    key=lambda item:
                        int(item[0]),
                )
            ),

        "duplicate_task_keys":
            duplicate_keys,
        "invalid_backlog_rows":
            invalid_rows,

        "provider_calls": 0,
        "web_calls": 0,

        "priority_is_only_collection_order":
            True,
        "venue_property_inference_allowed":
            False,

        "research_only":
            True,
        "operational_betting_authority":
            False,
        "creates_signal":
            False,
        "probability_mutation":
            False,
        "eligibility_mutation":
            False,
        "stake_changes":
            False,
        "forward_journal_mutation":
            False,

        "next_stage": (
            "Capture evidence-backed venue facts in batches; "
            "write verified dated values to pbk_venue_overrides.csv; "
            "rebuild Stage265 registry; never infer UNKNOWN values."
        ),
    }

    write_csv(
        backlog_path,
        tasks,
    )

    write_json(
        meta_path,
        meta,
    )

    return meta


def main():
    print(
        json.dumps(
            run(),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
