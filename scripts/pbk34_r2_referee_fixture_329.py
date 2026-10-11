
"""PBK34: referee assignments from archived fixture passports only."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_football_broker import request_key
from api_football_raw_archive import (
    read_archived_response,
    s3_config_from_env,
)

IDS = [
    1382720, 1382722, 1382723, 1382724,
    1382725, 1382730, 1382733, 1382738,
    1382751, 1382753, 1382754, 1396341,
]

INVALID = {
    "", "missing", "unknown", "pending", "none",
    "null", "n/a", "nan", "donor_only", "false",
}

if s3_config_from_env() is None:
    raise RuntimeError("R2_CREDENTIALS_NOT_CONFIGURED")

results = []
errors = 0

for fid in IDS:
    row = {
        "fixture_id": fid,
        "status": None,
        "referee": None,
        "source_endpoint": "/fixtures",
        "archive_only": True,
    }

    try:
        key = request_key("GET", "/fixtures", {"id": fid})
        data = read_archived_response(key)

        if data is None:
            row["status"] = "MISS"

        elif not isinstance(data, dict):
            row["status"] = "INVALID_RESPONSE"

        elif data.get("errors"):
            row["status"] = "PROVIDER_ERROR_IN_ARCHIVE"

        else:
            items = data.get("response")

            if not isinstance(items, list) or len(items) != 1:
                row["status"] = "INVALID_RESPONSE_COUNT"

            else:
                fixture = items[0].get("fixture") or {}
                actual = fixture.get("id")

                if str(actual) != str(fid):
                    row["status"] = "FIXTURE_ID_MISMATCH"

                else:
                    name = fixture.get("referee")
                    name = name.strip() if isinstance(name, str) else ""

                    if (
                        name.casefold() in INVALID
                        or not any(ch.isalpha() for ch in name)
                    ):
                        row["status"] = "HIT_WITHOUT_REFEREE"
                    else:
                        row["status"] = "HIT_WITH_REFEREE"
                        row["referee"] = name

    except Exception as exc:
        row["status"] = "READ_ERROR"
        row["error_type"] = type(exc).__name__
        errors += 1

    results.append(row)
    print(
        fid, row["status"],
        repr(row["referee"]),
        flush=True,
    )

output = {
    "contract": "PBK34_R2_REFEREE_FIXTURE_329",
    "requested_ids": IDS,
    "results": results,
    "archive_reads": len(IDS),
    "provider_api_calls": 0,
    "referee_assignments_promoted": 0,
    "betting_authority": False,
}

path = Path("ops/pbk34_r2_referee_fixture_329.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    json.dumps(output, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("OUTPUT =", path)
print("ARCHIVE READS =", len(IDS))
print("PROVIDER API CALLS = 0")

if errors:
    raise SystemExit("R2_READ_ERRORS_DETECTED")
