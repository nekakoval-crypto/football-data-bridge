#!/usr/bin/env python3
"""Stage80 — validate Transfermarkt enrichment source metadata.

Provider/network-free validator for the downloaded dcaribou transfermarkt-datasets
metadata. It verifies that the transfer table exists with the fields PBK plans to
ingest later, and records source provenance without pretending the source is live.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED = {
    "player_id",
    "player_name",
    "transfer_date",
    "transfer_season",
    "from_club_id",
    "to_club_id",
    "from_club_name",
    "to_club_name",
    "transfer_fee",
    "market_value_in_eur",
}


def find_table(metadata, name="transfers"):
    for item in metadata if isinstance(metadata, list) else metadata.get("resources", []):
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return None


def validate(path):
    metadata = json.loads(Path(path).read_text(encoding="utf-8"))
    table = find_table(metadata)
    if table is None:
        return {"status": "ATTENTION", "table": "transfers", "missing_table": True, "missing_fields": sorted(EXPECTED)}
    fields = {
        str(field.get("name"))
        for field in ((table.get("schema") or {}).get("fields") or [])
        if isinstance(field, dict) and field.get("name")
    }
    missing = sorted(EXPECTED - fields)
    return {
        "status": "OK" if not missing else "ATTENTION",
        "table": "transfers",
        "path": table.get("path"),
        "format": table.get("format"),
        "fields": sorted(fields),
        "missing_fields": missing,
        "source_role": "HISTORICAL_ENRICHMENT_SOURCE",
        "current_operational_authority": False,
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage80_transfer_source_audit.py dataset-metadata.json")
    report = validate(sys.argv[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "OK":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
