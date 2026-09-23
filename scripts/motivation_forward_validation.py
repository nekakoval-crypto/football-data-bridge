#!/usr/bin/env python3
"""PBK Item 13 ? prospective motivation validation rail.

Purpose:
- freeze motivation context strictly before kickoff;
- never historical-backfill a missed observation;
- keep prematch observations immutable;
- write postmatch labels into a separate append-only journal;
- provide validation-sample readiness without promoting motivation
  to probability or betting authority.

This module is provider-free. It consumes already-materialized PBK
current-round fixtures and standings snapshots.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from scripts import standings_motivation
    from scripts import standings_format_registry
except ModuleNotFoundError:
    import standings_motivation
    import standings_format_registry


VERSION = "PBK_ITEM13_MOTIVATION_FORWARD_VALIDATION_V1"

ROOT = Path(__file__).resolve().parents[1]
OPS = Path(os.getenv("OPS_DIR", str(ROOT / "ops")))

FIXTURES = OPS / "current_round_fixtures.csv"
SNAPSHOTS = OPS / "standings_snapshots.csv"

PREMATCH = OPS / "motivation_forward_prematch.jsonl"
LABELS = OPS / "motivation_forward_labels.jsonl"
LAST_RUN = OPS / "motivation_forward_validation_last_run.json"

CAPTURE_WINDOW_MINUTES = 90

ENGINEERING_CONTRACT = {
    "prematch_frozen_required": True,
    "historical_backfill_forbidden": True,
    "postmatch_label_separate_journal": True,
    "immutable_prematch_required": True,
    "no_lookahead": True,
    "provider_calls_added": 0,
    "research_only": True,
    "creates_signal": False,
    "probability_mutation": False,
    "eligibility_mutation": False,
    "stake_changes": False,
    "operational_betting_authority": False,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None

    try:
        result = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if result.tzinfo is None:
        return None

    return result.astimezone(timezone.utc)


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def read_jsonl(
    path: Path,
) -> tuple[bytes, list[dict[str, Any]]]:
    if not path.exists():
        return b"", []

    raw = path.read_bytes()
    rows = []

    for line_number, line in enumerate(
        raw.decode("utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        row = json.loads(line)

        if not isinstance(row, dict):
            raise ValueError(
                f"{path}:{line_number}: row must be object"
            )

        rows.append(row)

    ids = [
        str(row.get("event_id") or "")
        for row in rows
    ]

    if (
        any(not value for value in ids)
        or len(ids) != len(set(ids))
    ):
        raise ValueError(
            f"{path.name}: invalid or duplicate event_id"
        )

    return raw, rows


def atomic_append(
    path: Path,
    original: bytes,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    separator = (
        b"\n"
        if original
        and not original.endswith(b"\n")
        else b""
    )

    addition = b"".join(
        (
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        for row in rows
    )

    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    with tmp.open("wb") as handle:
        handle.write(
            original + separator + addition
        )
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(tmp, path)


def fingerprint(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def event_id(kind: str, *values: Any) -> str:
    material = "|".join(
        [
            VERSION,
            kind,
            *[
                str(value or "")
                for value in values
            ],
        ]
    )

    return hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()[:32]


def fixture_identity(
    fixture: dict[str, Any],
) -> str:
    return str(
        fixture.get("fixture_id")
        or fixture.get("api_fixture_id")
        or ""
    ).strip()


def snapshot_groups(
    rows: list[dict[str, Any]],
) -> dict[
    tuple[str, str, str],
    list[dict[str, Any]],
]:
    groups = {}

    for row in rows:
        league = str(
            row.get("provider_league_id") or ""
        ).strip()
        season = str(
            row.get("season") or ""
        ).strip()
        snapshot = str(
            row.get("snapshot_id") or ""
        ).strip()

        if not league or not season or not snapshot:
            continue

        groups.setdefault(
            (league, season, snapshot),
            [],
        ).append(row)

    return groups


def eligible_snapshot(
    fixture: dict[str, Any],
    snapshots: list[dict[str, Any]],
    observed_at: datetime,
) -> list[dict[str, Any]] | None:
    kickoff = parse_iso(
        fixture.get("kickoff_utc")
    )

    if kickoff is None:
        return None

    # Prospective-only: never reconstruct after kickoff.
    if observed_at >= kickoff:
        return None

    league = str(
        fixture.get("provider_league_id") or ""
    ).strip()
    season = str(
        fixture.get("season") or ""
    ).strip()

    candidates = []

    for (
        group_league,
        group_season,
        snapshot_id,
    ), rows in snapshot_groups(snapshots).items():
        if (
            group_league != league
            or group_season != season
        ):
            continue

        times = {
            parse_iso(
                row.get("observed_at_utc")
            )
            for row in rows
        }

        if None in times or len(times) != 1:
            continue

        snapshot_time = next(iter(times))

        if not (
            kickoff
            - timedelta(
                minutes=CAPTURE_WINDOW_MINUTES
            )
            <= snapshot_time
            <= observed_at
            < kickoff
        ):
            continue

        candidates.append(
            (
                snapshot_time,
                snapshot_id,
                rows,
            )
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: (
            item[0],
            item[1],
        ),
    )[2]


def normalize_fixture(
    row: dict[str, Any],
) -> dict[str, Any]:
    return {
        "fixture_id": fixture_identity(row),
        "provider_league_id": str(
            row.get("provider_league_id") or ""
        ).strip(),
        "season": str(
            row.get("season") or ""
        ).strip(),
        "kickoff_utc": row.get("kickoff_utc"),
        "home_team_id": (
            row.get("home_team_id")
            or None
        ),
        "away_team_id": (
            row.get("away_team_id")
            or None
        ),
        "home_team": row.get("home_team"),
        "away_team": row.get("away_team"),
    }


def prematch_event(
    fixture: dict[str, Any],
    motivation: dict[str, Any],
    frozen_at: datetime,
) -> dict[str, Any]:
    fid = fixture_identity(fixture)

    snapshot_id = (
        motivation
        .get("standings_context", {})
        .get("snapshot_id")
    )

    payload = {
        "fixture_id": fid,
        "provider_league_id": str(
            fixture.get(
                "provider_league_id"
            ) or ""
        ),
        "season": str(
            fixture.get("season") or ""
        ),
        "kickoff_utc": fixture.get(
            "kickoff_utc"
        ),
        "home_team": fixture.get(
            "home_team"
        ),
        "away_team": fixture.get(
            "away_team"
        ),
        "frozen_at_utc": iso(frozen_at),
        "snapshot_id": snapshot_id,
        "snapshot_observed_at_utc": (
            motivation
            .get("standings_context", {})
            .get(
                "snapshot_observed_at_utc"
            )
        ),
        "coverage": motivation.get(
            "coverage"
        ),
        "home": motivation.get("home"),
        "away": motivation.get("away"),
        "comparison": motivation.get(
            "comparison"
        ),
        "rivalry_context": motivation.get(
            "rivalry_context"
        ),
        "direct_rival_context": (
            motivation.get(
                "direct_rival_context"
            )
        ),
        "outcome_necessity": motivation.get(
            "outcome_necessity"
        ),
        "motivation_dimensions": (
            motivation.get(
                "motivation_dimensions"
            )
        ),
        "prematch_frozen": True,
        "result_hindsight_used": False,
        "research_only": True,
        "operational_betting_authority": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }

    eid = event_id(
        "MOTIVATION_PREMATCH_FROZEN",
        fid,
        snapshot_id,
    )

    return {
        "event_id": eid,
        "event_type": (
            "MOTIVATION_PREMATCH_FROZEN"
        ),
        "version": VERSION,
        "fixture_id": fid,
        "frozen_at_utc": iso(frozen_at),
        "immutable_fingerprint": (
            fingerprint(payload)
        ),
        "payload": payload,
    }


def final_score(
    row: dict[str, Any],
) -> tuple[int, int] | None:
    status = str(
        row.get("status")
        or row.get("source_status")
        or ""
    ).upper().strip()

    finished = {
        "FT",
        "AET",
        "PEN",
        "FINISHED",
        "SETTLED",
    }

    if status not in finished:
        return None

    try:
        home = int(
            str(
                row.get("score_home")
                or row.get("home_score")
                or ""
            ).strip()
        )
        away = int(
            str(
                row.get("score_away")
                or row.get("away_score")
                or ""
            ).strip()
        )
    except ValueError:
        return None

    return home, away


def label_event(
    prematch: dict[str, Any],
    fixture: dict[str, Any],
    labeled_at: datetime,
) -> dict[str, Any] | None:
    score = final_score(fixture)

    if score is None:
        return None

    kickoff = parse_iso(
        prematch
        .get("payload", {})
        .get("kickoff_utc")
    )

    if kickoff is None:
        return None

    if labeled_at <= kickoff:
        return None

    home_goals, away_goals = score

    if home_goals > away_goals:
        result = "HOME_WIN"
    elif away_goals > home_goals:
        result = "AWAY_WIN"
    else:
        result = "DRAW"

    payload = {
        "fixture_id": prematch[
            "fixture_id"
        ],
        "prematch_event_id": prematch[
            "event_id"
        ],
        "kickoff_utc": (
            prematch["payload"][
                "kickoff_utc"
            ]
        ),
        "labeled_at_utc": iso(
            labeled_at
        ),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "match_result": result,
        "total_goals": (
            home_goals + away_goals
        ),
        "both_teams_scored": (
            home_goals > 0
            and away_goals > 0
        ),
        "postmatch_factual": True,
        "prematch_evidence_mutated": False,
        "research_only": True,
        "operational_betting_authority": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }

    eid = event_id(
        "MOTIVATION_POSTMATCH_LABEL",
        prematch["event_id"],
    )

    return {
        "event_id": eid,
        "event_type": (
            "MOTIVATION_POSTMATCH_LABEL"
        ),
        "version": VERSION,
        "fixture_id": prematch[
            "fixture_id"
        ],
        "frozen_at_utc": iso(
            labeled_at
        ),
        "immutable_fingerprint": (
            fingerprint(payload)
        ),
        "payload": payload,
    }


def engineering_readiness(
    prematch_rows: list[
        dict[str, Any]
    ] | None = None,
    label_rows: list[
        dict[str, Any]
    ] | None = None,
) -> dict[str, Any]:
    prematch_rows = (
        []
        if prematch_rows is None
        else prematch_rows
    )
    label_rows = (
        []
        if label_rows is None
        else label_rows
    )

    prematch_ids = {
        row.get("event_id")
        for row in prematch_rows
        if row.get("event_type")
        == "MOTIVATION_PREMATCH_FROZEN"
    }

    valid_labels = [
        row
        for row in label_rows
        if (
            row.get("event_type")
            == "MOTIVATION_POSTMATCH_LABEL"
            and row.get(
                "payload", {}
            ).get("prematch_event_id")
            in prematch_ids
        )
    ]

    return {
        "version": VERSION,
        "engineering_status": "COMPLETE",
        "forward_validation_rail": True,
        "prematch_observation_contract": (
            "APPEND_ONLY_PREMATCH_FROZEN"
        ),
        "postmatch_label_contract": (
            "SEPARATE_APPEND_ONLY_POSTMATCH"
        ),
        "prospective_only": True,
        "historical_backfill": "FORBIDDEN",
        "no_lookahead": True,
        "prematch_events": len(
            prematch_ids
        ),
        "labeled_events": len(
            valid_labels
        ),
        "unlabeled_events": max(
            0,
            len(prematch_ids)
            - len(valid_labels),
        ),
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "predictive_authority": (
            "NOT_AUTHORIZED"
        ),
    }


def run(
    *,
    observed_at: datetime | None = None,
    ops: Path = OPS,
) -> dict[str, Any]:
    observed_at = (
        observed_at or utc_now()
    ).astimezone(timezone.utc)

    fixtures_path = (
        ops / FIXTURES.name
    )
    snapshots_path = (
        ops / SNAPSHOTS.name
    )
    prematch_path = (
        ops / PREMATCH.name
    )
    labels_path = (
        ops / LABELS.name
    )
    last_run_path = (
        ops / LAST_RUN.name
    )

    fixtures = read_csv(
        fixtures_path
    )
    snapshots = read_csv(
        snapshots_path
    )

    prematch_raw, prematch = (
        read_jsonl(prematch_path)
    )
    labels_raw, labels = (
        read_jsonl(labels_path)
    )

    prematch_by_fixture = {
        str(row.get("fixture_id") or ""):
        row
        for row in prematch
        if row.get("event_type")
        == "MOTIVATION_PREMATCH_FROZEN"
    }

    labels_by_prematch = {
        str(
            row.get(
                "payload", {}
            ).get(
                "prematch_event_id"
            ) or ""
        ):
        row
        for row in labels
        if row.get("event_type")
        == "MOTIVATION_POSTMATCH_LABEL"
    }

    new_prematch = []
    new_labels = []

    drift = 0
    capture_candidates = 0
    skipped_after_kickoff = 0
    skipped_no_snapshot = 0
    skipped_unavailable = 0

    for raw_fixture in fixtures:
        fid = fixture_identity(
            raw_fixture
        )

        kickoff = parse_iso(
            raw_fixture.get(
                "kickoff_utc"
            )
        )

        if not fid or kickoff is None:
            continue

        existing = (
            prematch_by_fixture.get(
                fid
            )
        )

        # Never reconstruct missed prematch context.
        if existing is None:
            if observed_at >= kickoff:
                skipped_after_kickoff += 1
                continue

            rows = eligible_snapshot(
                raw_fixture,
                snapshots,
                observed_at,
            )

            if not rows:
                skipped_no_snapshot += 1
                continue

            capture_candidates += 1

            fixture = normalize_fixture(
                raw_fixture
            )

            fmt = (
                standings_format_registry
                .get_format(
                    fixture[
                        "provider_league_id"
                    ],
                    fixture["season"],
                )
            )

            motivation = (
                standings_motivation
                .analyze_fixture(
                    fixture,
                    rows,
                    format_meta=fmt,
                )
            )

            if not motivation.get(
                "available"
            ):
                skipped_unavailable += 1
                continue

            candidate = prematch_event(
                raw_fixture,
                motivation,
                observed_at,
            )

            new_prematch.append(
                candidate
            )

            prematch_by_fixture[
                fid
            ] = candidate

            existing = candidate

        # If the source is now settled, add only a separate label.
        if (
            existing["event_id"]
            in labels_by_prematch
        ):
            continue

        candidate_label = label_event(
            existing,
            raw_fixture,
            observed_at,
        )

        if candidate_label is not None:
            new_labels.append(
                candidate_label
            )

            labels_by_prematch[
                existing["event_id"]
            ] = candidate_label

    # Detect immutable identity drift inside candidate batches.
    existing_prematch_ids = {
        row["event_id"]: row
        for row in prematch
    }

    for row in new_prematch:
        old = existing_prematch_ids.get(
            row["event_id"]
        )

        if (
            old is not None
            and old.get(
                "immutable_fingerprint"
            )
            != row.get(
                "immutable_fingerprint"
            )
        ):
            drift += 1

    existing_label_ids = {
        row["event_id"]: row
        for row in labels
    }

    for row in new_labels:
        old = existing_label_ids.get(
            row["event_id"]
        )

        if (
            old is not None
            and old.get(
                "immutable_fingerprint"
            )
            != row.get(
                "immutable_fingerprint"
            )
        ):
            drift += 1

    if drift:
        raise ValueError(
            "Immutable motivation journal drift detected"
        )

    atomic_append(
        prematch_path,
        prematch_raw,
        new_prematch,
    )

    atomic_append(
        labels_path,
        labels_raw,
        new_labels,
    )

    all_prematch = (
        prematch + new_prematch
    )
    all_labels = (
        labels + new_labels
    )

    readiness = engineering_readiness(
        all_prematch,
        all_labels,
    )

    meta = {
        **readiness,
        "run_at_utc": iso(
            observed_at
        ),
        "fixtures_seen": len(
            fixtures
        ),
        "snapshot_rows_seen": len(
            snapshots
        ),
        "capture_candidates": (
            capture_candidates
        ),
        "prematch_events_created": len(
            new_prematch
        ),
        "labels_created": len(
            new_labels
        ),
        "skipped_after_kickoff_no_backfill": (
            skipped_after_kickoff
        ),
        "skipped_no_eligible_snapshot": (
            skipped_no_snapshot
        ),
        "skipped_unavailable_motivation": (
            skipped_unavailable
        ),
        "immutable_drift_detected": (
            drift
        ),
        "provider_calls_added": 0,
    }

    last_run_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    last_run_path.write_text(
        json.dumps(
            meta,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return meta


def main() -> int:
    result = run()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
