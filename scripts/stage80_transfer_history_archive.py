#!/usr/bin/env python3
"""Stage80 — durable PBK historical transfer-event archive.

Consumes the conservative PBK ↔ Transfermarkt mapping artifacts produced by
stage80_transfer_entity_mapping.py and persists only HIGH-confidence
EXACT_NAME_CURRENT_CLUB transfer evidence.

The archive is provider-free and append-only: an existing transfer_event_id is
never rewritten. If a later source snapshot disagrees with the first observed
row for the same event identity, the first observation remains authoritative
and the conflict is reported in telemetry.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

VERSION = "PBK_STAGE80_TRANSFER_HISTORY_ARCHIVE_V1"
SAFE_METHOD = "EXACT_NAME_CURRENT_CLUB"
SAFE_CONFIDENCE = "HIGH"
SAFE_STATUS = "AUTO_MATCH"

FIELDS = [
    "transfer_event_id",
    "pbk_player_id",
    "pbk_player_name",
    "transfermarkt_player_id",
    "transfermarkt_player_name",
    "transfer_date",
    "transfer_season",
    "from_club_id",
    "from_club_name",
    "to_club_id",
    "to_club_name",
    "transfer_fee",
    "market_value_in_eur",
    "mapping_method",
    "mapping_confidence",
    "source",
    "source_snapshot",
    "source_metadata_sha256",
    "ingested_at_utc",
    "archive_version",
    "research_only",
    "creates_signal",
    "probability_mutation",
    "eligibility_mutation",
    "stake_changes",
    "forward_journal_mutation",
    "current_operational_authority",
]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def file_sha256(path):
    path = Path(path)
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata_snapshot(path):
    path = Path(path)
    sha = file_sha256(path)
    if not path.exists():
        return "", sha
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError):
        return sha, sha

    def find_value(value):
        if isinstance(value, dict):
            for key in (
                "snapshot_date",
                "last_updated",
                "last_update",
                "updated_at",
                "generated_at",
                "date",
                "version",
            ):
                candidate = value.get(key)
                if candidate not in (None, ""):
                    return str(candidate).strip()
            for child in value.values():
                found = find_value(child)
                if found:
                    return found
        return ""

    label = find_value(payload)
    return label or sha, sha


def mapping_index(mapping_rows):
    safe = {}
    for row in mapping_rows:
        if (
            sval(row, "match_status") != SAFE_STATUS
            or sval(row, "match_method") != SAFE_METHOD
            or sval(row, "match_confidence") != SAFE_CONFIDENCE
        ):
            continue
        pbk_id = sval(row, "pbk_player_id")
        tm_id = sval(row, "transfermarkt_player_id")
        if not pbk_id or not tm_id:
            continue
        key = (pbk_id, tm_id)
        if key in safe:
            # Ambiguous duplicates are intentionally not authoritative.
            safe[key] = None
            continue
        safe[key] = {
            "pbk_player_name": sval(row, "pbk_player_name"),
            "transfermarkt_player_name": sval(row, "transfermarkt_player_name"),
        }
    return {key: value for key, value in safe.items() if value is not None}


def transfer_event_id(row):
    pbk_id = sval(row, "pbk_player_id")
    tm_id = sval(row, "transfermarkt_player_id")
    transfer_date = sval(row, "transfer_date")
    from_key = sval(row, "from_club_id") or sval(row, "from_club_name")
    to_key = sval(row, "to_club_id") or sval(row, "to_club_name")
    season = sval(row, "transfer_season")
    if not pbk_id or not tm_id or not transfer_date:
        return ""
    material = "\x1f".join([pbk_id, tm_id, transfer_date, season, from_key, to_key])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def normalize_mapped_rows(mapped_rows, mapping_rows, source_snapshot="", metadata_sha="", ingested_at_utc=None):
    ingested_at_utc = ingested_at_utc or now_iso()
    safe = mapping_index(mapping_rows)
    output = []
    rejected = 0
    invalid_identity = 0

    for row in mapped_rows:
        pbk_id = sval(row, "pbk_player_id")
        tm_id = sval(row, "transfermarkt_player_id")
        mapped = safe.get((pbk_id, tm_id))
        if (
            mapped is None
            or sval(row, "mapping_method") != SAFE_METHOD
            or sval(row, "mapping_confidence") != SAFE_CONFIDENCE
        ):
            rejected += 1
            continue

        base = {
            "pbk_player_id": pbk_id,
            "pbk_player_name": mapped["pbk_player_name"],
            "transfermarkt_player_id": tm_id,
            "transfermarkt_player_name": sval(row, "player_name") or mapped["transfermarkt_player_name"],
            "transfer_date": sval(row, "transfer_date"),
            "transfer_season": sval(row, "transfer_season"),
            "from_club_id": sval(row, "from_club_id"),
            "from_club_name": sval(row, "from_club_name"),
            "to_club_id": sval(row, "to_club_id"),
            "to_club_name": sval(row, "to_club_name"),
            "transfer_fee": sval(row, "transfer_fee"),
            "market_value_in_eur": sval(row, "market_value_in_eur"),
            "mapping_method": SAFE_METHOD,
            "mapping_confidence": SAFE_CONFIDENCE,
            "source": sval(row, "source") or "dcaribou/transfermarkt-datasets:transfers",
            "source_snapshot": source_snapshot,
            "source_metadata_sha256": metadata_sha,
            "ingested_at_utc": ingested_at_utc,
            "archive_version": VERSION,
            "research_only": "true",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
            "current_operational_authority": "false",
        }
        base["transfer_event_id"] = transfer_event_id(base)
        if not base["transfer_event_id"]:
            invalid_identity += 1
            continue
        output.append(base)

    output.sort(
        key=lambda row: (
            row["pbk_player_id"],
            row["transfer_date"],
            row["transfer_event_id"],
        )
    )
    return output, rejected, invalid_identity


def row_signature(row):
    return tuple(sval(row, field) for field in FIELDS if field != "ingested_at_utc")


def merge_first_observation(existing_rows, candidate_rows):
    merged = {}
    duplicate_rows = 0
    conflicts = 0
    invalid_existing = 0

    for row in existing_rows:
        event_id = sval(row, "transfer_event_id")
        if not event_id:
            invalid_existing += 1
            continue
        if event_id not in merged:
            merged[event_id] = {field: sval(row, field) for field in FIELDS}
        elif row_signature(merged[event_id]) != row_signature(row):
            conflicts += 1
        else:
            duplicate_rows += 1

    added = 0
    for row in candidate_rows:
        event_id = sval(row, "transfer_event_id")
        if event_id not in merged:
            merged[event_id] = {field: sval(row, field) for field in FIELDS}
            added += 1
        elif row_signature(merged[event_id]) == row_signature(row):
            duplicate_rows += 1
        else:
            conflicts += 1

    rows = list(merged.values())
    rows.sort(
        key=lambda row: (
            sval(row, "pbk_player_id"),
            sval(row, "transfer_date"),
            sval(row, "transfer_event_id"),
        )
    )
    return rows, {
        "added_rows": added,
        "duplicate_rows": duplicate_rows,
        "conflicts_preserved_first_observation": conflicts,
        "invalid_existing_identity_rows": invalid_existing,
    }


def run(mapped_path, mapping_path, metadata_path, existing_path, out_path, meta_out):
    mapped_rows = read_csv(mapped_path)
    mapping_rows = read_csv(mapping_path)
    existing_rows = read_csv(existing_path) if existing_path else []
    source_snapshot, metadata_sha = metadata_snapshot(metadata_path)
    ingested_at = now_iso()

    candidates, rejected, invalid_identity = normalize_mapped_rows(
        mapped_rows,
        mapping_rows,
        source_snapshot=source_snapshot,
        metadata_sha=metadata_sha,
        ingested_at_utc=ingested_at,
    )
    merged, merge_meta = merge_first_observation(existing_rows, candidates)
    write_csv(out_path, merged)

    meta = {
        "version": VERSION,
        "run_at_utc": ingested_at,
        "source_snapshot": source_snapshot,
        "source_metadata_sha256": metadata_sha,
        "mapped_input_rows": len(mapped_rows),
        "safe_candidate_rows": len(candidates),
        "rejected_non_authoritative_rows": rejected,
        "invalid_candidate_identity_rows": invalid_identity,
        "existing_rows": len(existing_rows),
        "archive_rows": len(merged),
        **merge_meta,
        "mapping_policy": "AUTO_MATCH+EXACT_NAME_CURRENT_CLUB+HIGH_ONLY",
        "provider_calls": 0,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "current_operational_authority": False,
    }
    Path(meta_out).parent.mkdir(parents=True, exist_ok=True)
    Path(meta_out).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapped", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--existing", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--meta-out", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.mapped,
                args.mapping,
                args.metadata,
                args.existing or None,
                args.out,
                args.meta_out,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
