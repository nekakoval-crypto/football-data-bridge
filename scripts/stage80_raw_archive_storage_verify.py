#!/usr/bin/env python3
"""Verify durable S3/R2 raw archive storage by write -> readback -> SHA-256."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from api_football_raw_archive import verify_s3_storage

OPS = Path(os.getenv("OPS_DIR", "ops"))
OUT = OPS / "stage80_raw_archive_storage_last_run.json"
VERSION = "PBK_STAGE80_RAW_ARCHIVE_STORAGE_VERIFY_V1"


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    result = verify_s3_storage(keep_object=True)
    report = {
        "version": VERSION,
        "run_at_utc": now.isoformat().replace("+00:00", "Z"),
        **result,
        "provider_calls": 0,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    OPS.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if report["status"] != "READY" or not report["readback_match"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
