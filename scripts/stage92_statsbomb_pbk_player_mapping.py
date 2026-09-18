#!/usr/bin/env python3
"""Stage92 — conservative StatsBomb ↔ PBK player identity bridge.

Authority rules:
- AUTO_MATCH/HIGH is allowed only when a StatsBomb full player name exactly
  matches a UNIQUE Transfermarkt full name already linked to a PBK player by
  the verified Stage80 EXACT_NAME_CURRENT_CLUB/HIGH transfer mapping.
- API-Football abbreviated names (for example "M. Akanji") may create REVIEW
  candidates by first-initial + surname, but can never become authority here.
- Only AUTO_MATCH/HIGH rows are allowed into pbk_player_xg_xa_research.csv.

No provider/network calls are made.
"""
from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

VERSION = "PBK_STAGE92_STATSBOMB_PBK_PLAYER_MAPPING_V1"
AUTO_METHOD = "EXACT_FULL_NAME_VIA_VERIFIED_TRANSFER"
REVIEW_METHOD = "INITIAL_SURNAME_PBK_CANDIDATE"
TRANSFER_METHODS = {"EXACT_NAME_CURRENT_CLUB", "EXACT_PROFILE_NAME_DOB_CURRENT_CLUB", "EXACT_STATS_NAME_CURRENT_CLUB"}
TRANSFER_CONFIDENCE = "HIGH"

MAPPING_FIELDS = [
    "statsbomb_player_id",
    "statsbomb_player_name",
    "statsbomb_match_rows",
    "statsbomb_match_count",
    "pbk_player_id",
    "pbk_player_name",
    "transfermarkt_player_ids",
    "transfermarkt_player_names",
    "match_status",
    "match_method",
    "match_confidence",
    "authoritative_for_player_xg_xa",
    "review_candidate_count",
    "review_candidate_pbk_ids",
    "review_candidate_pbk_names",
    "source",
    "research_only",
    "creates_signal",
    "probability_mutation",
    "eligibility_mutation",
    "stake_changes",
    "forward_journal_mutation",
]

MAPPED_FIELDS = [
    "pbk_player_id",
    "pbk_player_name",
    "statsbomb_player_id",
    "statsbomb_player_name",
    "statsbomb_match_id",
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
    "mapping_method",
    "mapping_confidence",
    "statsbomb_record_id",
    "source_event_sha256",
    "source_revision",
    "source",
    "attribution_required",
    "research_only",
    "operational_betting_authority",
    "creates_signal",
    "probability_mutation",
    "eligibility_mutation",
    "stake_changes",
    "forward_journal_mutation",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def sval(value: Any) -> str:
    return str(value if value is not None else "").strip()


def normalized_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", sval(value))
    text = text.replace("’", "'").replace(chr(96), "'")
    return " ".join(text.casefold().split())


def initial_surname_key(value: Any) -> str:
    name = normalized_name(value)
    if not name:
        return ""
    tokens = name.replace(",", " ").split()
    if len(tokens) < 2:
        return ""
    first = tokens[0].strip(".")
    surname = tokens[-1].strip(".")
    if not first or not surname:
        return ""
    return f"{first[0]}|{surname}"


def verified_transfer_bridge(
    transfer_rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, dict[tuple[str, str], dict[str, str]]] = defaultdict(dict)
    for row in transfer_rows:
        if (
            sval(row.get("mapping_method")) not in TRANSFER_METHODS
            or sval(row.get("mapping_confidence")) != TRANSFER_CONFIDENCE
        ):
            continue
        pbk_id = sval(row.get("pbk_player_id"))
        pbk_name = sval(row.get("pbk_player_name"))
        tm_id = sval(row.get("transfermarkt_player_id"))
        tm_name = sval(row.get("transfermarkt_player_name"))
        key = normalized_name(tm_name)
        if not pbk_id or not tm_id or not key:
            continue
        grouped[key][(pbk_id, tm_id)] = {
            "pbk_player_id": pbk_id,
            "pbk_player_name": pbk_name,
            "transfermarkt_player_id": tm_id,
            "transfermarkt_player_name": tm_name,
        }
    return {
        key: list(items.values())
        for key, items in grouped.items()
    }


def historical_review_index(
    historical_rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in historical_rows:
        pbk_id = sval(row.get("player_id"))
        name = sval(row.get("latest_observed_name"))
        key = initial_surname_key(name)
        if not pbk_id or not key:
            continue
        grouped[key][pbk_id] = {
            "pbk_player_id": pbk_id,
            "pbk_player_name": name,
        }
    return {key: list(items.values()) for key, items in grouped.items()}


def statsbomb_players(
    source_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in source_rows:
        player_id = sval(row.get("statsbomb_player_id"))
        player_name = sval(row.get("player_name"))
        match_id = sval(row.get("statsbomb_match_id"))
        if not player_id or not player_name:
            continue
        item = grouped.setdefault(
            player_id,
            {
                "statsbomb_player_id": player_id,
                "names": set(),
                "match_rows": 0,
                "matches": set(),
            },
        )
        item["names"].add(player_name)
        item["match_rows"] += 1
        if match_id:
            item["matches"].add(match_id)

    result = []
    for player_id, item in grouped.items():
        names = sorted(item["names"], key=normalized_name)
        result.append(
            {
                "statsbomb_player_id": player_id,
                "statsbomb_player_name": names[0] if names else "",
                "statsbomb_name_variants": names,
                "statsbomb_match_rows": item["match_rows"],
                "statsbomb_match_count": len(item["matches"]),
            }
        )
    result.sort(key=lambda row: row["statsbomb_player_id"])
    return result


def build_mapping(
    source_rows: list[dict[str, str]],
    transfer_rows: list[dict[str, str]],
    historical_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    bridge = verified_transfer_bridge(transfer_rows)
    review_index = historical_review_index(historical_rows)
    output = []

    for player in statsbomb_players(source_rows):
        player_id = player["statsbomb_player_id"]
        player_name = player["statsbomb_player_name"]
        variants = player["statsbomb_name_variants"]
        exact_entries = bridge.get(normalized_name(player_name), [])
        exact_pbk_ids = {entry["pbk_player_id"] for entry in exact_entries}

        row = {
            "statsbomb_player_id": player_id,
            "statsbomb_player_name": player_name,
            "statsbomb_match_rows": player["statsbomb_match_rows"],
            "statsbomb_match_count": player["statsbomb_match_count"],
            "pbk_player_id": "",
            "pbk_player_name": "",
            "transfermarkt_player_ids": "",
            "transfermarkt_player_names": "",
            "match_status": "UNMATCHED",
            "match_method": "NONE",
            "match_confidence": "NONE",
            "authoritative_for_player_xg_xa": "false",
            "review_candidate_count": 0,
            "review_candidate_pbk_ids": "",
            "review_candidate_pbk_names": "",
            "source": "Stage92 StatsBomb→verified Transfermarkt→PBK bridge",
            "research_only": "true",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        }

        if len(variants) > 1:
            row["match_status"] = "REVIEW"
            row["match_method"] = "STATSBOMB_PLAYER_ID_NAME_DRIFT"
            row["match_confidence"] = "LOW"
            output.append(row)
            continue

        if exact_entries and len(exact_pbk_ids) == 1:
            pbk_id = next(iter(exact_pbk_ids))
            pbk_entries = [entry for entry in exact_entries if entry["pbk_player_id"] == pbk_id]
            row.update(
                {
                    "pbk_player_id": pbk_id,
                    "pbk_player_name": pbk_entries[0]["pbk_player_name"],
                    "transfermarkt_player_ids": "|".join(sorted({e["transfermarkt_player_id"] for e in pbk_entries})),
                    "transfermarkt_player_names": "|".join(sorted({e["transfermarkt_player_name"] for e in pbk_entries})),
                    "match_status": "AUTO_MATCH",
                    "match_method": AUTO_METHOD,
                    "match_confidence": "HIGH",
                    "authoritative_for_player_xg_xa": "true",
                }
            )
            output.append(row)
            continue

        review = review_index.get(initial_surname_key(player_name), [])
        row["review_candidate_count"] = len(review)
        row["review_candidate_pbk_ids"] = "|".join(sorted({x["pbk_player_id"] for x in review}))
        row["review_candidate_pbk_names"] = "|".join(sorted({x["pbk_player_name"] for x in review}))

        if review:
            row["match_status"] = "REVIEW"
            row["match_method"] = REVIEW_METHOD
            row["match_confidence"] = "MEDIUM" if len(review) == 1 else "LOW"
            if len(review) == 1:
                row["pbk_player_id"] = review[0]["pbk_player_id"]
                row["pbk_player_name"] = review[0]["pbk_player_name"]

        output.append(row)

    return output


def authoritative_index(mapping_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for row in mapping_rows:
        if (
            sval(row.get("match_status")) == "AUTO_MATCH"
            and sval(row.get("match_method")) == AUTO_METHOD
            and sval(row.get("match_confidence")) == "HIGH"
            and sval(row.get("authoritative_for_player_xg_xa")).lower() == "true"
            and sval(row.get("statsbomb_player_id"))
            and sval(row.get("pbk_player_id"))
        ):
            result[sval(row.get("statsbomb_player_id"))] = row
    return result


def map_research_metrics(
    source_rows: list[dict[str, str]],
    mapping_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    index = authoritative_index(mapping_rows)
    output = []
    seen = set()
    for source in source_rows:
        sb_id = sval(source.get("statsbomb_player_id"))
        mapping = index.get(sb_id)
        if mapping is None:
            continue
        record_id = sval(source.get("record_id"))
        match_id = sval(source.get("statsbomb_match_id"))
        team_id = sval(source.get("statsbomb_team_id"))
        key = (mapping["pbk_player_id"], record_id or f"{match_id}|{sb_id}|{team_id}")
        if key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "pbk_player_id": mapping["pbk_player_id"],
                "pbk_player_name": mapping["pbk_player_name"],
                "statsbomb_player_id": sb_id,
                "statsbomb_player_name": sval(source.get("player_name")) or mapping["statsbomb_player_name"],
                "statsbomb_match_id": match_id,
                "statsbomb_team_id": team_id,
                "team_name": sval(source.get("team_name")),
                "match_date": sval(source.get("match_date")),
                "competition_id": sval(source.get("competition_id")),
                "competition_name": sval(source.get("competition_name")),
                "season_id": sval(source.get("season_id")),
                "season_name": sval(source.get("season_name")),
                "shots": sval(source.get("shots")),
                "non_penalty_shots": sval(source.get("non_penalty_shots")),
                "penalty_shots": sval(source.get("penalty_shots")),
                "xg_total": sval(source.get("xg_total")),
                "npxg": sval(source.get("npxg")),
                "penalty_xg": sval(source.get("penalty_xg")),
                "assisted_shots": sval(source.get("assisted_shots")),
                "xa": sval(source.get("xa")),
                "mapping_method": AUTO_METHOD,
                "mapping_confidence": "HIGH",
                "statsbomb_record_id": record_id,
                "source_event_sha256": sval(source.get("source_event_sha256")),
                "source_revision": sval(source.get("source_revision")),
                "source": "StatsBomb Open Data via Stage91 + Stage92 verified identity bridge",
                "attribution_required": "true",
                "research_only": "true",
                "operational_betting_authority": "false",
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
                "forward_journal_mutation": "false",
            }
        )
    output.sort(
        key=lambda row: (
            sval(row.get("pbk_player_id")),
            sval(row.get("statsbomb_match_id")),
            sval(row.get("statsbomb_team_id")),
        )
    )
    return output


def run(
    source_path: Path,
    transfer_path: Path,
    historical_path: Path,
    mapping_out: Path,
    mapped_out: Path,
    meta_out: Path,
    identity_path: Path | None = None,
) -> dict[str, Any]:
    source_rows = read_csv(source_path)
    transfer_rows = read_csv(transfer_path)
    identity_rows = read_csv(identity_path) if identity_path and identity_path.exists() else []
    bridge_rows = identity_rows or transfer_rows
    historical_rows = read_csv(historical_path)

    mapping_rows = build_mapping(source_rows, bridge_rows, historical_rows)
    mapped_rows = map_research_metrics(source_rows, mapping_rows)

    write_csv(mapping_out, MAPPING_FIELDS, mapping_rows)
    write_csv(mapped_out, MAPPED_FIELDS, mapped_rows)

    counts = defaultdict(int)
    for row in mapping_rows:
        counts[sval(row.get("match_status"))] += 1

    status = "OK" if source_rows else "WAITING_FOR_STAGE91_MATERIALIZATION"
    meta = {
        "version": VERSION,
        "status": status,
        "source_rows": len(source_rows),
        "source_unique_statsbomb_players": len(statsbomb_players(source_rows)),
        "verified_transfer_rows": len(transfer_rows),
        "verified_identity_rows": len(identity_rows),
        "identity_bridge_source": "pbk_transfermarkt_player_identity.csv" if identity_rows else "historical_transfer_events.csv_fallback",
        "historical_player_rows": len(historical_rows),
        "mapping_rows": len(mapping_rows),
        "auto_match_high": counts["AUTO_MATCH"],
        "review": counts["REVIEW"],
        "unmatched": counts["UNMATCHED"],
        "mapped_research_rows": len(mapped_rows),
        "auto_match_method": AUTO_METHOD,
        "review_method": REVIEW_METHOD,
        "review_is_authoritative": False,
        "mapped_output_requires_auto_high": True,
        "provider_calls": 0,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    meta_out.parent.mkdir(parents=True, exist_ok=True)
    meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--transfers", required=True)
    parser.add_argument("--historical-players", required=True)
    parser.add_argument("--identity-map", default="")
    parser.add_argument("--mapping-out", required=True)
    parser.add_argument("--mapped-out", required=True)
    parser.add_argument("--meta-out", required=True)
    args = parser.parse_args()

    result = run(
        Path(args.source),
        Path(args.transfers),
        Path(args.historical_players),
        Path(args.mapping_out),
        Path(args.mapped_out),
        Path(args.meta_out),
        identity_path=Path(args.identity_map) if args.identity_map else None,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
