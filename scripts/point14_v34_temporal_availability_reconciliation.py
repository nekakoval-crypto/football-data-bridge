#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))

HIST_LINEUPS = OPS / "historical_lineup_snapshots.csv"
LIVE_LINEUPS = OPS / "lineup_snapshots.csv"
JOURNAL = OPS / "player_availability_prematch_events.csv"
INJURIES = OPS / "injury_snapshots.csv"

TARGETED = Path(
    os.getenv(
        "PBK_V34_TARGETED_AVAILABILITY",
        "point14_v34_targeted_player_availability.csv",
    )
)

SEASON_LEDGER = Path(
    os.getenv(
        "PBK_V34_SEASON_INJURY_LEDGER",
        "point14_v34_current_injury_universe.csv",
    )
)

OUT = OPS / "point14_v34_temporal_availability_reconciliation.json"

VERSION = "PBK_POINT14_V34_TEMPORAL_AVAILABILITY_RECONCILIATION_V1"


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def read_csv(path):
    if not path.exists():
        return []

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def dt(value):
    raw = str(value or "").strip()

    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        )
        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )
        return parsed.astimezone(
            timezone.utc
        )
    except Exception:
        try:
            return datetime.strptime(
                raw[:10],
                "%Y-%m-%d",
            ).replace(
                tzinfo=timezone.utc
            )
        except Exception:
            return None


def iso(value):
    if value is None:
        return ""

    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_json_list(value):
    try:
        data = json.loads(value)
    except Exception:
        return []

    return data if isinstance(data, list) else []


def lineup_contains_player(row, player_id):
    for player in parse_json_list(
        row.get("starting_xi_json")
    ):
        if not isinstance(player, dict):
            continue

        pid = str(
            player.get("id")
            or player.get("player_id")
            or ""
        ).strip()

        if pid == player_id:
            return True

    return False


def latest_official_start(lineups, *, player_id, team_id):
    candidates = []

    for row in lineups:
        if sval(row, "team_id") != team_id:
            continue

        # Two lineup ledgers have different contracts:
        #
        # 1) lineup_snapshots.csv
        #    provider-free Stage80 normalized evidence;
        #    explicit official_lineup flag must be true.
        #
        # 2) historical_lineup_snapshots.csv
        #    API-Football /fixtures/lineups capture;
        #    no official_lineup column exists.
        #    A complete 11-player row from that endpoint is
        #    retrospective factual XI evidence.
        official_flag = sval(
            row,
            "official_lineup",
        ).upper()

        source_endpoint = sval(
            row,
            "source_endpoint",
        ).lower()

        temporal_authority = sval(
            row,
            "temporal_authority",
        ).upper()

        try:
            xi_count = int(
                sval(
                    row,
                    "starting_xi_count",
                )
                or "0"
            )
        except ValueError:
            xi_count = 0

        normalized_official = (
            official_flag
            in {
                "YES",
                "TRUE",
                "1",
            }
        )

        historical_factual = (
            source_endpoint
            == "/fixtures/lineups"
            and xi_count == 11
            and temporal_authority
            == "RETROSPECTIVE_ONLY"
        )

        if not (
            normalized_official
            or historical_factual
        ):
            continue

        if not lineup_contains_player(
            row,
            player_id,
        ):
            continue

        kickoff = dt(
            row.get("kickoff_utc")
        )

        if kickoff is None:
            continue

        candidates.append(
            (
                kickoff,
                {
                    "fixture_id": sval(
                        row,
                        "fixture_id",
                    ),
                    "kickoff_utc": iso(
                        kickoff
                    ),
                    "captured_at_utc": sval(
                        row,
                        "captured_at_utc",
                    ),
                    "source": (
                        sval(
                            row,
                            "source_dataset",
                        )
                        or sval(
                            row,
                            "source_endpoint",
                        )
                    ),
                    "temporal_authority": sval(
                        row,
                        "temporal_authority",
                    ),
                    "official_lineup_flag": sval(
                        row,
                        "official_lineup",
                    ),
                },
            )
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: item[0],
    )[1]


def latest_journal_event(
    journal,
    *,
    player_id,
    team_id,
    states,
):
    candidates = []

    for row in journal:
        if sval(row, "player_id") != player_id:
            continue

        if sval(row, "team_id") != team_id:
            continue

        state = sval(
            row,
            "state",
        ).upper()

        if state not in states:
            continue

        observed = dt(
            row.get("observed_at_utc")
        )

        if observed is None:
            continue

        candidates.append(
            (
                observed,
                {
                    "state": state,
                    "fixture_id": sval(
                        row,
                        "fixture_id",
                    ),
                    "kickoff_utc": sval(
                        row,
                        "kickoff_utc",
                    ),
                    "observed_at_utc": iso(
                        observed
                    ),
                    "availability_type": sval(
                        row,
                        "availability_type",
                    ),
                    "reason": sval(
                        row,
                        "reason",
                    ),
                    "source": sval(
                        row,
                        "source",
                    ),
                    "evidence_type": sval(
                        row,
                        "evidence_type",
                    ),
                },
            )
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: item[0],
    )[1]


def latest_injury_snapshot(
    injuries,
    *,
    player_id,
    team_id,
):
    candidates = []

    for row in injuries:
        if sval(row, "player_id") != player_id:
            continue

        if sval(row, "team_id") != team_id:
            continue

        observed = dt(
            row.get("captured_at_utc")
        )

        if observed is None:
            continue

        candidates.append(
            (
                observed,
                {
                    "fixture_id": sval(
                        row,
                        "fixture_id",
                    ),
                    "kickoff_utc": sval(
                        row,
                        "kickoff_utc",
                    ),
                    "observed_at_utc": iso(
                        observed
                    ),
                    "availability_type": sval(
                        row,
                        "availability_type",
                    ),
                    "reason": sval(
                        row,
                        "reason",
                    ),
                    "source": (
                        sval(
                            row,
                            "source_dataset",
                        )
                        or sval(
                            row,
                            "source_endpoint",
                        )
                    ),
                    "temporal_authority": sval(
                        row,
                        "temporal_authority",
                    ),
                    "official_lineup_flag": sval(
                        row,
                        "official_lineup",
                    ),
                },
            )
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: item[0],
    )[1]


def latest_season_ledger_event(
    rows,
    *,
    player_id,
    team_id,
):
    candidates = []

    for row in rows:
        if sval(row, "player_id") != player_id:
            continue

        if sval(row, "team_id") != team_id:
            continue

        fixture_date = dt(
            row.get("fixture_date")
        )

        if fixture_date is None:
            # V34.2 output may contain fixture id but
            # provider date can be absent.
            continue

        candidates.append(
            (
                fixture_date,
                {
                    "fixture_id": sval(
                        row,
                        "fixture_id",
                    ),
                    "fixture_date": iso(
                        fixture_date
                    ),
                    "type": sval(
                        row,
                        "type",
                    ),
                    "reason": sval(
                        row,
                        "reason",
                    ),
                    "captured_at_utc": sval(
                        row,
                        "captured_at_utc",
                    ),
                    "source": (
                        "V34_SEASON_INJURY_LEDGER"
                    ),
                },
            )
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: item[0],
    )[1]


def evidence_time(evidence):
    if not evidence:
        return None

    for key in (
        "kickoff_utc",
        "observed_at_utc",
        "fixture_date",
        "captured_at_utc",
    ):
        parsed = dt(
            evidence.get(key)
        )
        if parsed is not None:
            return parsed

    return None


def newest_injury_evidence(
    journal_absent,
    injury_snapshot,
    season_ledger,
):
    candidates = []

    for source_name, evidence in (
        (
            "JOURNAL_ABSENT",
            journal_absent,
        ),
        (
            "INJURY_SNAPSHOT",
            injury_snapshot,
        ),
        (
            "SEASON_LEDGER",
            season_ledger,
        ),
    ):
        when = evidence_time(
            evidence
        )

        if when is not None:
            candidates.append(
                (
                    when,
                    source_name,
                    evidence,
                )
            )

    if not candidates:
        return None

    when, source_name, evidence = max(
        candidates,
        key=lambda item: item[0],
    )

    return {
        "source_class": source_name,
        "effective_at_utc": iso(when),
        "evidence": evidence,
    }


def reconcile(
    *,
    targeted,
    latest_start,
    journal_present,
    journal_absent,
    injury_snapshot,
    season_ledger,
):
    injury = newest_injury_evidence(
        journal_absent,
        injury_snapshot,
        season_ledger,
    )

    start_time = evidence_time(
        latest_start
    )

    present_time = evidence_time(
        journal_present
    )

    recovery_candidates = [
        value
        for value in (
            start_time,
            present_time,
        )
        if value is not None
    ]

    recovery_time = (
        max(recovery_candidates)
        if recovery_candidates
        else None
    )

    injury_time = (
        dt(injury["effective_at_utc"])
        if injury
        else None
    )

    flag_observed = dt(
        targeted.get("captured_at_utc")
    )

    player_flag = sval(
        targeted,
        "player_injured",
    ).upper()

    sidelined_open = (
        sval(
            targeted,
            "latest_sidelined_open",
        ).upper()
        == "YES"
    )

    sidelined_start = dt(
        targeted.get(
            "latest_sidelined_start"
        )
    )

    # Strong chronology first.
    if (
        injury_time is not None
        and recovery_time is not None
    ):
        if recovery_time > injury_time:
            return {
                "status": (
                    "LAST_PROVEN_AVAILABLE"
                ),
                "reason": (
                    "Official-start/presence evidence "
                    "is newer than injury evidence."
                ),
            }

        if injury_time > recovery_time:
            return {
                "status": (
                    "LAST_PROVEN_UNAVAILABLE"
                ),
                "reason": (
                    "Explicit injury/absence evidence "
                    "is newer than last proven official "
                    "start/presence."
                ),
            }

    if (
        injury_time is not None
        and recovery_time is None
    ):
        return {
            "status": (
                "LAST_PROVEN_UNAVAILABLE"
            ),
            "reason": (
                "Explicit injury/absence evidence exists "
                "and no later official-start/presence "
                "evidence is available."
            ),
        }

    # Provider current flag is weak positive evidence,
    # never a strong clearance when FALSE.
    if player_flag == "TRUE":
        return {
            "status": (
                "LAST_PROVEN_UNAVAILABLE"
            ),
            "reason": (
                "Fresh player.injured=TRUE provider flag."
            ),
        }

    # Open sidelined is conflict/uncertainty unless
    # chronology gives us a later proven start.
    if sidelined_open:
        if (
            recovery_time is not None
            and sidelined_start is not None
            and recovery_time > sidelined_start
        ):
            return {
                "status": (
                    "CONFLICTING_EVIDENCE"
                ),
                "reason": (
                    "Open sidelined episode conflicts with "
                    "newer proven official-start/presence."
                ),
            }

        return {
            "status": (
                "CONFLICTING_EVIDENCE"
            ),
            "reason": (
                "Open sidelined episode exists but is not "
                "trusted as standalone OUT authority."
            ),
        }

    # FALSE does not prove fit.
    if (
        player_flag == "FALSE"
        and recovery_time is not None
    ):
        return {
            "status": (
                "LAST_PROVEN_AVAILABLE"
            ),
            "reason": (
                "Recent proven official-start/presence "
                "exists; player.injured=FALSE is only "
                "supporting evidence."
            ),
        }

    return {
        "status": (
            "INSUFFICIENT_CURRENT_EVIDENCE"
        ),
        "reason": (
            "No sufficiently strong chronological evidence "
            "to assert availability or unavailability."
        ),
    }


def main():
    targeted_rows = read_csv(
        TARGETED
    )
    season_rows = read_csv(
        SEASON_LEDGER
    )
    # Same lineup evidence universe used by Point14 V23:
    # current-season backfill can live in historical_lineup_snapshots,
    # while provider-free Stage80 materialization lives in lineup_snapshots.
    lineups = (
        read_csv(HIST_LINEUPS)
        + read_csv(LIVE_LINEUPS)
    )
    journal = read_csv(
        JOURNAL
    )
    injuries = read_csv(
        INJURIES
    )

    results = []

    for targeted in targeted_rows:
        player_id = sval(
            targeted,
            "player_id",
        )
        team_id = sval(
            targeted,
            "team_id",
        )

        if not player_id or not team_id:
            continue

        latest_start = latest_official_start(
            lineups,
            player_id=player_id,
            team_id=team_id,
        )

        journal_present = latest_journal_event(
            journal,
            player_id=player_id,
            team_id=team_id,
            states={"PRESENT"},
        )

        journal_absent = latest_journal_event(
            journal,
            player_id=player_id,
            team_id=team_id,
            states={"ABSENT"},
        )

        injury_snapshot = latest_injury_snapshot(
            injuries,
            player_id=player_id,
            team_id=team_id,
        )

        season_ledger = latest_season_ledger_event(
            season_rows,
            player_id=player_id,
            team_id=team_id,
        )

        decision = reconcile(
            targeted=targeted,
            latest_start=latest_start,
            journal_present=journal_present,
            journal_absent=journal_absent,
            injury_snapshot=injury_snapshot,
            season_ledger=season_ledger,
        )

        results.append({
            "kind": sval(
                targeted,
                "kind",
            ),
            "team_id": team_id,
            "team_name": sval(
                targeted,
                "team_name",
            ),
            "player_id": player_id,
            "player_name": sval(
                targeted,
                "roster_player_name",
            ),

            "player_injured": sval(
                targeted,
                "player_injured",
            ),
            "player_flag_observed_at_utc": sval(
                targeted,
                "captured_at_utc",
            ),

            "latest_sidelined_type": sval(
                targeted,
                "latest_sidelined_type",
            ),
            "latest_sidelined_start": sval(
                targeted,
                "latest_sidelined_start",
            ),
            "latest_sidelined_end": sval(
                targeted,
                "latest_sidelined_end",
            ),
            "latest_sidelined_open": sval(
                targeted,
                "latest_sidelined_open",
            ),

            "latest_official_start": latest_start,
            "latest_journal_present": journal_present,
            "latest_journal_absent": journal_absent,
            "latest_injury_snapshot": injury_snapshot,
            "latest_season_ledger_event": season_ledger,

            "last_proven_state": decision[
                "status"
            ],
            "last_proven_state_reason": decision[
                "reason"
            ],

            # IMPORTANT:
            # Historical/current evidence chronology does NOT prove
            # availability for a future target fixture.
            "target_fixture_availability": (
                "UNCERTAIN_PENDING_FRESH_MATCH_EVIDENCE"
            ),
            "target_fixture_hard_exclusion": False,
        })

    counts = {}

    for row in results:
        status = row[
            "last_proven_state"
        ]
        counts[status] = (
            counts.get(status, 0) + 1
        )

    report = {
        "version": VERSION,
        "run_at_utc": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),

        "targeted_source": str(
            TARGETED
        ),
        "season_ledger_source": str(
            SEASON_LEDGER
        ),

        "target_count": len(
            targeted_rows
        ),
        "reconciled_count": len(
            results
        ),

        "status_counts": counts,
        "players": results,

        "rules": {
            "official_start_after_injury": (
                "RECOVERY_EVIDENCE"
            ),
            "injury_after_official_start": (
                "LAST_PROVEN_UNAVAILABLE"
            ),
            "player_injured_true": (
                "SUPPORTS_UNAVAILABLE"
            ),
            "player_injured_false": (
                "NEVER_STANDALONE_CLEARANCE"
            ),
            "open_sidelined": (
                "CONFLICT_OR_UNCERTAINTY_ONLY"
            ),
            "absence_from_lineup": (
                "NEVER_INFERRED_AS_ABSENT"
            ),
        },

        "provider_calls": 0,
        "provider_free": True,

        "semantic_contract": {
            "last_proven_state": (
                "LATEST_STRONG_EVIDENCE_STATE_ONLY"
            ),
            "future_fixture_availability": (
                "NOT_INFERRED_FROM_LAST_PROVEN_STATE"
            ),
            "fresh_fixture_specific_evidence_required": True,
            "player_injured_false_is_clearance": False,
            "open_sidelined_is_standalone_out": False,
            "future_recovery_possible": True,
        },

        "mutates_probable_xi": False,
        "probability_status": "UNCALIBRATED",
        "research_only": True,
        "operational_betting_authority": False,
    }

    OUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print("=" * 130)
    print("PBK V34.4 — TEMPORAL AVAILABILITY RECONCILIATION")
    print("=" * 130)

    for row in results:
        start = (
            row.get("latest_official_start")
            or {}
        )

        injury = (
            row.get("latest_season_ledger_event")
            or row.get("latest_injury_snapshot")
            or row.get("latest_journal_absent")
            or {}
        )

        print()
        print(
            f"{row['team_name']} | "
            f"{row['player_name']} "
            f"(id={row['player_id']})"
        )

        print(
            "  PLAYER FLAG :",
            row["player_injured"],
            "@",
            row["player_flag_observed_at_utc"],
        )

        print(
            "  SIDELINED   :",
            row["latest_sidelined_type"],
            row["latest_sidelined_start"],
            "->",
            row["latest_sidelined_end"]
            or "OPEN",
        )

        print(
            "  LAST START  :",
            start.get(
                "kickoff_utc",
                "NONE",
            ),
            "fixture=",
            start.get(
                "fixture_id",
                "",
            ),
        )

        print(
            "  LAST INJURY :",
            injury.get(
                "fixture_date",
                injury.get(
                    "observed_at_utc",
                    injury.get(
                        "kickoff_utc",
                        "NONE",
                    ),
                ),
            ),
            injury.get(
                "reason",
                "",
            ),
        )

        print(
            "  RESULT      :",
            row[
                "last_proven_state"
            ],
        )

        print(
            "  WHY         :",
            row[
                "last_proven_state_reason"
            ],
        )

    print()
    print("=" * 130)
    print("STATUS COUNTS")
    print("=" * 130)
    print(
        json.dumps(
            counts,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("provider_calls=0")
    print("mutates_probable_xi=False")
    print("research_only=True")


if __name__ == "__main__":
    main()




