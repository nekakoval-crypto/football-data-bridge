#!/usr/bin/env python3
"""Stage91 — provider-free StatsBomb Open Data player xG/xA research projection.

This adapter consumes a LOCAL StatsBomb Open Data checkout. It never downloads
or redistributes raw StatsBomb event files.

Player xG is a source metric from shot.statsbomb_xg.

Player xA is a derived research metric following StatsBomb's documented xG
Assisted method: for a shot carrying shot.key_pass_id, join that identifier
to the creating pass event and assign the shot's xG value to the passer.

The output remains in the StatsBomb identity namespace. No API-Football/PBK
player identity is inferred here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

VERSION = "PBK_STAGE91_STATSBOMB_PLAYER_XG_XA_V1"
SOURCE = "StatsBomb Open Data"
SOURCE_REPO = "https://github.com/hudl/open-data"
XG_SOURCE_FIELD = "shot.statsbomb_xg"
XA_METHOD = "JOIN_PASS_EVENT_ID_TO_SHOT_KEY_PASS_ID_THEN_ASSIGN_SHOT_XG"

FIELDS = [
    "record_id",
    "statsbomb_match_id",
    "statsbomb_player_id",
    "player_name",
    "statsbomb_team_id",
    "team_name",
    "match_date",
    "competition_id",
    "competition_name",
    "season_id",
    "season_name",
    "shots",
    "non_penalty_shots",
    "penalty_shots",
    "xg_total",
    "npxg",
    "penalty_xg",
    "assisted_shots",
    "xa",
    "xg_source_field",
    "xa_derivation_method",
    "source",
    "source_repository",
    "source_event_sha256",
    "source_revision",
    "attribution_required",
    "research_only",
    "operational_betting_authority",
    "creates_signal",
    "probability_mutation",
    "eligibility_mutation",
    "stake_changes",
    "forward_journal_mutation",
]


def finite_number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def sval(value: Any) -> str:
    return str(value if value is not None else "").strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_match_metadata(matches_root: Path | None) -> dict[str, dict[str, str]]:
    if matches_root is None or not matches_root.exists():
        return {}
    result: dict[str, dict[str, str]] = {}
    for path in sorted(matches_root.rglob("*.json")):
        payload = read_json(path)
        if not isinstance(payload, list):
            continue
        for match in payload:
            if not isinstance(match, dict):
                continue
            match_id = sval(match.get("match_id"))
            if not match_id:
                continue
            competition = match.get("competition") or {}
            season = match.get("season") or {}
            result[match_id] = {
                "match_date": sval(match.get("match_date")),
                "competition_id": sval(competition.get("competition_id")),
                "competition_name": sval(competition.get("competition_name")),
                "season_id": sval(season.get("season_id")),
                "season_name": sval(season.get("season_name")),
            }
    return result


def player_key(match_id: str, player_id: str, team_id: str) -> tuple[str, str, str]:
    return match_id, player_id, team_id


def new_accumulator(
    match_id: str,
    player: dict[str, Any],
    team: dict[str, Any],
    metadata: dict[str, str],
    source_hash: str,
    source_revision: str,
) -> dict[str, Any]:
    return {
        "statsbomb_match_id": match_id,
        "statsbomb_player_id": sval(player.get("id")),
        "player_name": sval(player.get("name")),
        "statsbomb_team_id": sval(team.get("id")),
        "team_name": sval(team.get("name")),
        **metadata,
        "shots": 0,
        "non_penalty_shots": 0,
        "penalty_shots": 0,
        "xg_total": 0.0,
        "npxg": 0.0,
        "penalty_xg": 0.0,
        "assisted_shots": 0,
        "xa": 0.0,
        "xg_source_field": XG_SOURCE_FIELD,
        "xa_derivation_method": XA_METHOD,
        "source": SOURCE,
        "source_repository": SOURCE_REPO,
        "source_event_sha256": source_hash,
        "source_revision": source_revision,
        "attribution_required": "true",
        "research_only": "true",
        "operational_betting_authority": "false",
        "creates_signal": "false",
        "probability_mutation": "false",
        "eligibility_mutation": "false",
        "stake_changes": "false",
        "forward_journal_mutation": "false",
    }


def ensure_player(
    acc: dict[tuple[str, str, str], dict[str, Any]],
    match_id: str,
    event: dict[str, Any],
    metadata: dict[str, str],
    source_hash: str,
    source_revision: str,
) -> dict[str, Any] | None:
    player = event.get("player") or {}
    team = event.get("team") or {}
    player_id = sval(player.get("id"))
    team_id = sval(team.get("id"))
    if not player_id or not team_id:
        return None
    key = player_key(match_id, player_id, team_id)
    if key not in acc:
        acc[key] = new_accumulator(
            match_id, player, team, metadata, source_hash, source_revision
        )
    return acc[key]


def record_id(row: dict[str, Any]) -> str:
    material = "\x1f".join(
        [
            sval(row.get("statsbomb_match_id")),
            sval(row.get("statsbomb_player_id")),
            sval(row.get("statsbomb_team_id")),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def round_metric(value: float) -> str:
    return f"{value:.9f}"


def project_event_file(
    path: Path,
    metadata: dict[str, str] | None = None,
    source_revision: str = "",
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    match_id = path.stem
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a JSON event list")

    source_hash = sha256_file(path)
    metadata = metadata or {}
    events = [item for item in payload if isinstance(item, dict)]
    by_event_id = {
        sval(event.get("id")): event
        for event in events
        if sval(event.get("id"))
    }

    acc: dict[tuple[str, str, str], dict[str, Any]] = {}
    xg_shots = 0
    invalid_xg_shots = 0
    xa_links = 0
    xa_unmatched = 0
    xa_team_mismatch = 0

    for event in events:
        if sval((event.get("type") or {}).get("name")) != "Shot":
            continue
        shot = event.get("shot") or {}
        xg = finite_number(shot.get("statsbomb_xg"))
        if xg is None or xg < 0:
            invalid_xg_shots += 1
            continue
        row = ensure_player(
            acc, match_id, event, metadata, source_hash, source_revision
        )
        if row is None:
            invalid_xg_shots += 1
            continue

        xg_shots += 1
        row["shots"] += 1
        row["xg_total"] += xg

        shot_type = sval((shot.get("type") or {}).get("name"))
        if shot_type == "Penalty":
            row["penalty_shots"] += 1
            row["penalty_xg"] += xg
        else:
            row["non_penalty_shots"] += 1
            row["npxg"] += xg

        key_pass_id = sval(shot.get("key_pass_id"))
        if not key_pass_id:
            continue
        creator = by_event_id.get(key_pass_id)
        if creator is None or sval((creator.get("type") or {}).get("name")) != "Pass":
            xa_unmatched += 1
            continue

        shot_team_id = sval((event.get("team") or {}).get("id"))
        creator_team_id = sval((creator.get("team") or {}).get("id"))
        if shot_team_id and creator_team_id and shot_team_id != creator_team_id:
            xa_team_mismatch += 1
            continue

        creator_row = ensure_player(
            acc, match_id, creator, metadata, source_hash, source_revision
        )
        if creator_row is None:
            xa_unmatched += 1
            continue
        creator_row["assisted_shots"] += 1
        creator_row["xa"] += xg
        xa_links += 1

    rows = []
    for row in acc.values():
        output = dict(row)
        output["record_id"] = record_id(output)
        for field in ("xg_total", "npxg", "penalty_xg", "xa"):
            output[field] = round_metric(float(output[field]))
        rows.append(output)
    rows.sort(
        key=lambda row: (
            sval(row.get("statsbomb_match_id")),
            sval(row.get("statsbomb_team_id")),
            sval(row.get("statsbomb_player_id")),
        )
    )
    return rows, {
        "events": len(events),
        "xg_shots": xg_shots,
        "invalid_xg_shots": invalid_xg_shots,
        "xa_links": xa_links,
        "xa_unmatched": xa_unmatched,
        "xa_team_mismatch": xa_team_mismatch,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run(
    events_dir: Path,
    matches_root: Path | None,
    out: Path,
    meta_out: Path,
    source_revision: str = "",
) -> dict[str, Any]:
    if not events_dir.exists():
        raise FileNotFoundError(events_dir)

    metadata = load_match_metadata(matches_root)
    all_rows: list[dict[str, Any]] = []
    totals = defaultdict(int)
    event_files = sorted(events_dir.glob("*.json"))

    for path in event_files:
        match_meta = metadata.get(path.stem, {})
        rows, stats = project_event_file(
            path,
            metadata=match_meta,
            source_revision=source_revision,
        )
        all_rows.extend(rows)
        for key, value in stats.items():
            totals[key] += value

    all_rows.sort(
        key=lambda row: (
            sval(row.get("statsbomb_match_id")),
            sval(row.get("statsbomb_team_id")),
            sval(row.get("statsbomb_player_id")),
        )
    )
    ids = [row["record_id"] for row in all_rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate Stage91 record_id")

    write_csv(out, all_rows)
    meta = {
        "version": VERSION,
        "status": "OK",
        "events_dir_files": len(event_files),
        "matches_with_player_rows": len(
            {row["statsbomb_match_id"] for row in all_rows}
        ),
        "player_match_rows": len(all_rows),
        "unique_statsbomb_players": len(
            {row["statsbomb_player_id"] for row in all_rows}
        ),
        "xg_shots": totals["xg_shots"],
        "invalid_xg_shots": totals["invalid_xg_shots"],
        "xa_links": totals["xa_links"],
        "xa_unmatched": totals["xa_unmatched"],
        "xa_team_mismatch": totals["xa_team_mismatch"],
        "source": SOURCE,
        "source_repository": SOURCE_REPO,
        "source_revision": source_revision,
        "raw_data_committed_to_pbk": False,
        "attribution_required": True,
        "xg_authority": "SOURCE_METRIC",
        "xa_authority": "DERIVED_RESEARCH_METRIC",
        "xa_derivation_method": XA_METHOD,
        "pbk_identity_mapping": "NOT_IMPLEMENTED",
        "research_only": True,
        "operational_betting_authority": False,
        "provider_calls": 0,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    meta_out.parent.mkdir(parents=True, exist_ok=True)
    meta_out.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-dir", required=True)
    parser.add_argument("--matches-root", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--meta-out", required=True)
    parser.add_argument("--source-revision", default="")
    args = parser.parse_args()

    result = run(
        Path(args.events_dir),
        Path(args.matches_root) if args.matches_root else None,
        Path(args.out),
        Path(args.meta_out),
        source_revision=args.source_revision,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
