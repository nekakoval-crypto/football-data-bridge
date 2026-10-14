from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import shutil


ROOT = Path(__file__).resolve().parents[1]

CAPTURE = ROOT / "ops" / "pbk16_capture_universe.csv"
FIXTURES = ROOT / "ops" / "current_round_fixtures.csv"
CONTEXT = ROOT / "ops" / "context_latest.csv"
# PBK493_UNIQUE_CONTEXT_BACKUP
BACKUP = (
    ROOT / "ops" / "checkpoints" /
    (
        "PBK35_CONTEXT_PREWRITE_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        + ".csv"
    )
)
META = ROOT / "ops" / "pbk_point14_current_context_adapter_v1_meta.json"


def read_csv(path):
    if not path.exists():
        return [], []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream)
        return list(reader), list(reader.fieldnames or [])


capture_rows, capture_fields = read_csv(CAPTURE)
fixture_rows, fixture_fields = read_csv(FIXTURES)
context_rows, context_fields = read_csv(CONTEXT)


if not capture_rows:
    raise SystemExit("Capture universe is empty")

capture_ids = [
    str(row.get("api_fixture_id") or "").strip()
    for row in capture_rows
]

if any(not item for item in capture_ids):
    raise SystemExit("Capture universe has empty fixture IDs")

if len(set(capture_ids)) != len(capture_ids):
    raise SystemExit("Capture universe has duplicate fixture IDs")

fixture_ids = [
    str(row.get("fixture_id") or "").strip()
    for row in fixture_rows
    if str(row.get("fixture_id") or "").strip()
]

if len(set(fixture_ids)) != len(fixture_ids):
    raise SystemExit("Current round has duplicate fixture IDs")

missing_ids = sorted(set(capture_ids) - set(fixture_ids))

if missing_ids:
    raise SystemExit(
        f"Capture fixture IDs missing from current round: {missing_ids}"
    )

fixture_lookup = {
    str(row.get("fixture_id") or "").strip(): row
    for row in fixture_rows
}

missing_kickoff = [
    item for item in capture_ids
    if not (
        str(
            fixture_lookup[item].get("kickoff_utc") or ""
        ).strip()
        or str(
            next(
                row for row in capture_rows
                if str(row.get("api_fixture_id") or "").strip() == item
            ).get("kickoff_utc") or ""
        ).strip()
    )
]

if missing_kickoff:
    raise SystemExit(
        f"Missing kickoff UTC for fixtures: {missing_kickoff}"
    )

expected_capture_rows = len(capture_rows)


if CONTEXT.exists():
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        CONTEXT,
        BACKUP,
    )


fixture_by_id = {
    str(
        row.get("fixture_id")
        or ""
    ).strip(): row
    for row in fixture_rows
    if str(
        row.get("fixture_id")
        or ""
    ).strip()
}


context_by_forward = {
    str(
        row.get("forward_id")
        or ""
    ).strip(): dict(row)
    for row in context_rows
    if str(
        row.get("forward_id")
        or ""
    ).strip()
}


required_fields = [
    "forward_id",
    "rule",
    "api_fixture_id",
    "captured_at_utc",
    "current_kickoff_utc",
    "fixture_status",
    "league",
    "home_team",
    "away_team",
    "home_team_id",
    "away_team_id",
    "referee",
    "venue_name",
    "venue_city",
]


all_fields = list(context_fields)

for field in required_fields:
    if field not in all_fields:
        all_fields.append(field)


now = datetime.now(timezone.utc)
now_text = (
    now.isoformat()
    .replace("+00:00", "Z")
)


matched = 0
missing_fixture = []
missing_city = []
new_rows = 0
updated_rows = 0


for capture in capture_rows:

    forward_id = str(
        capture.get("forward_id")
        or ""
    ).strip()

    fixture_id = str(
        capture.get("api_fixture_id")
        or capture.get("fixture_id")
        or ""
    ).strip()

    if not forward_id:
        raise SystemExit(
            f"Capture row without forward_id for fixture {fixture_id}"
        )

    fixture = fixture_by_id.get(
        fixture_id
    )

    if fixture is None:
        missing_fixture.append(
            fixture_id
        )
        continue

    matched += 1

    existing = context_by_forward.get(
        forward_id
    )

    if existing is None:
        existing = {
            field: ""
            for field in all_fields
        }
        context_by_forward[
            forward_id
        ] = existing
        new_rows += 1
    else:
        updated_rows += 1

    existing["forward_id"] = forward_id

    existing["rule"] = str(
        capture.get("rule")
        or existing.get("rule")
        or ""
    ).strip()

    existing["api_fixture_id"] = (
        fixture_id
    )

    existing["captured_at_utc"] = (
        now_text
    )

    existing["current_kickoff_utc"] = str(
        fixture.get("kickoff_utc")
        or ""
    ).strip()

    existing["fixture_status"] = str(
        fixture.get("source_status")
        or fixture.get("status")
        or ""
    ).strip()

    existing["league"] = str(
        fixture.get("league_name")
        or ""
    ).strip()

    existing["home_team"] = str(
        fixture.get("home_team")
        or capture.get("home_team")
        or ""
    ).strip()

    existing["away_team"] = str(
        fixture.get("away_team")
        or capture.get("away_team")
        or ""
    ).strip()

    existing["home_team_id"] = str(
        fixture.get("home_team_id")
        or ""
    ).strip()

    existing["away_team_id"] = str(
        fixture.get("away_team_id")
        or ""
    ).strip()

    existing["referee"] = str(
        fixture.get("referee")
        or ""
    ).strip()

    existing["venue_name"] = str(
        fixture.get("venue_name")
        or ""
    ).strip()

    existing["venue_city"] = str(
        fixture.get("venue_city")
        or ""
    ).strip()

    if not existing["venue_city"]:
        missing_city.append({
            "fixture_id": fixture_id,
            "forward_id": forward_id,
            "home_team": existing["home_team"],
            "away_team": existing["away_team"],
            "venue_name": existing["venue_name"],
        })


ordered = []

capture_forward_ids = [
    str(
        row.get("forward_id")
        or ""
    ).strip()
    for row in capture_rows
]


for forward_id in capture_forward_ids:
    row = context_by_forward.get(
        forward_id
    )

    if row is not None:
        ordered.append(
            {
                field: row.get(
                    field,
                    "",
                )
                for field in all_fields
            }
        )


capture_set = set(
    capture_forward_ids
)


for forward_id, row in context_by_forward.items():
    if forward_id in capture_set:
        continue

    ordered.append(
        {
            field: row.get(
                field,
                "",
            )
            for field in all_fields
        }
    )


# PBK478_PREWRITE_GATE
expected_ids = {
    str(row.get("forward_id") or "").strip()
    for row in capture_rows
}

actual_current_rows = [
    row for row in ordered
    if str(row.get("forward_id") or "").strip() in expected_ids
]

actual_ids = [
    str(row.get("forward_id") or "").strip()
    for row in actual_current_rows
]

if matched != expected_capture_rows:
    raise SystemExit(
        f"PREWRITE: fixture matches {matched}/{expected_capture_rows}"
    )

if len(actual_current_rows) != expected_capture_rows:
    raise SystemExit(
        "PREWRITE: current context row count mismatch"
    )

if len(set(actual_ids)) != len(actual_ids):
    raise SystemExit(
        "PREWRITE: duplicate current context identities"
    )

if set(actual_ids) != expected_ids:
    raise SystemExit(
        "PREWRITE: current fixture identity mismatch"
    )

missing_current_kickoff = [
    str(row.get("forward_id") or "").strip()
    for row in actual_current_rows
    if not str(row.get("current_kickoff_utc") or "").strip()
]

if missing_current_kickoff:
    raise SystemExit(
        f"PREWRITE: missing kickoff: {missing_current_kickoff}"
    )

print(
    f"PBK478 PREWRITE GATE = PASS ({expected_capture_rows} fixtures)"
)

# PBK524_VERIFIED_VENUE_CITY
# Exact fixture + nation + venue identity required.
# Coordinates remain city-level proxies, not stadium points.
_pbk524_sites = {
    "1553197": ("Poland", "Synerise Arena", "Krakow"),
    "1547639": ("Lithuania", "Aukstaitijos", "Panevezys"),
    "1584430": ("Turkey", "Diyarbakir Stadium", "Diyarbakir"),
}

import unicodedata as _pbk524_unicode

def _pbk524_norm(value):
    value = str(value or "").replace("ı", "i")
    decomposed = _pbk524_unicode.normalize("NFKD", value)
    return "".join(
        ch for ch in decomposed
        if not _pbk524_unicode.combining(ch)
    ).casefold().strip()

_pbk524_capture = {
    str(row.get("api_fixture_id") or ""): row
    for row in capture_rows
}
_pbk524_fixed = []

for _pbk524_row in ordered:
    _pbk524_fixture = str(
        _pbk524_row.get("api_fixture_id") or ""
    ).strip()
    _pbk524_rule = _pbk524_sites.get(_pbk524_fixture)
    if _pbk524_rule is None:
        continue

    _pbk524_country, _pbk524_venue, _pbk524_city = _pbk524_rule
    _pbk524_source = _pbk524_capture.get(_pbk524_fixture)

    if _pbk524_source is None:
        continue

    if str(_pbk524_source.get("country") or "").strip() != _pbk524_country:
        raise RuntimeError(
            f"PBK524 country identity mismatch: {_pbk524_fixture}"
        )

    _pbk524_actual_venue = _pbk524_norm(
        _pbk524_row.get("venue_name")
    )
    if _pbk524_norm(_pbk524_venue) not in _pbk524_actual_venue:
        raise RuntimeError(
            f"PBK524 venue identity mismatch: {_pbk524_fixture}"
        )

    if not str(_pbk524_row.get("venue_city") or "").strip():
        _pbk524_row["venue_city"] = _pbk524_city
        _pbk524_fixed.append(_pbk524_fixture)

if len(_pbk524_fixed) != len(set(_pbk524_fixed)):
    raise RuntimeError("PBK524 duplicate city recovery")

with CONTEXT.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as stream:

    writer = csv.DictWriter(
        stream,
        fieldnames=all_fields,
        extrasaction="ignore",
    )

    writer.writeheader()
    writer.writerows(
        ordered
    )


current_context_rows = [
    row
    for row in ordered
    if str(
        row.get("forward_id")
        or ""
    ).strip()
    in capture_set
]


current_with_city = sum(
    bool(
        str(
            row.get("venue_city")
            or ""
        ).strip()
    )
    for row in current_context_rows
)


current_with_venue = sum(
    bool(
        str(
            row.get("venue_name")
            or ""
        ).strip()
    )
    for row in current_context_rows
)


current_with_kickoff = sum(
    bool(
        str(
            row.get("current_kickoff_utc")
            or ""
        ).strip()
    )
    for row in current_context_rows
)


meta = {
    "version": (
        "PBK_POINT14_CURRENT_CONTEXT_ADAPTER_V1"
    ),
    "status": "OK",
    "capture_rows": len(
        capture_rows
    ),
    "fixture_rows": len(
        fixture_rows
    ),
    "matched_capture_fixtures": matched,
    "new_context_rows": new_rows,
    "updated_context_rows": updated_rows,
    "output_context_rows": len(
        ordered
    ),
    "current_context_rows": len(
        current_context_rows
    ),
    "current_with_kickoff": (
        current_with_kickoff
    ),
    "current_with_venue_name": (
        current_with_venue
    ),
    "current_with_venue_city": (
        current_with_city
    ),
    "missing_fixture_ids": (
        missing_fixture
    ),
    "missing_venue_city": (
        missing_city
    ),
    "source": (
        "SAVED_CURRENT_ROUND_FIXTURES"
    ),
    "api_football_calls": 0,
    "open_meteo_calls": 0,
    "predictive_authority": (
        "NOT_AUTHORIZED"
    ),
    "betting_authority": False,
}


META.write_text(
    json.dumps(
        meta,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)


print(
    json.dumps(
        meta,
        ensure_ascii=False,
        indent=2,
    )
)


if matched != expected_capture_rows:
    raise SystemExit(
        f"Expected {expected_capture_rows} fixture matches, got {matched}"
    )


if len(current_context_rows) != expected_capture_rows:
    raise SystemExit(
        f"Current context did not reach {expected_capture_rows} rows"
    )


if current_with_kickoff != expected_capture_rows:
    raise SystemExit(
        f"Kickoff coverage only {current_with_kickoff}/{expected_capture_rows}"
    )


print()
print("POINT14G = COMPLETE")
print("API-FOOTBALL CALLS = 0")
print("OPEN-METEO CALLS = 0")
