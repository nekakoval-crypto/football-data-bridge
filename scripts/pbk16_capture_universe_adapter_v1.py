from __future__ import annotations

import csv
from datetime import datetime, timezone

from pbk_data_registry import resolve

SOURCE_ID = "PBK.CURRENT_ROUND.FIXTURES.V1"
OUTPUT_ID = "PBK.CAPTURE_UNIVERSE.PBK16.V1"

SOURCE = resolve(
    SOURCE_ID,
    require_class="EVIDENCE",
    require_scope="CURRENT",
    require_prematch=True,
)[0]

OUTPUT = resolve(
    OUTPUT_ID,
    require_class="DERIVED",
    require_scope="CURRENT",
    require_prematch=True,
)[0]

FIELDS = [
    "forward_id",
    "rule",
    "status",
    "api_fixture_id",
    "match_date",
    "kickoff_time",
    "kickoff_utc",
    "league",
    "country",
    "provider_league_id",
    "home_team",
    "away_team",
    "home_team_id",
    "away_team_id",
    "source_dataset",
    "capture_authority",
]


def read_csv(path):
    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as fh:
        return list(csv.DictReader(fh))


def parse_iso(value):
    s = str(value or "").strip()

    if not s:
        return None

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


rows = read_csv(SOURCE)

out = []
seen = set()

for r in rows:

    fixture_id = str(
        r.get("fixture_id") or ""
    ).strip()

    kickoff = parse_iso(
        r.get("kickoff_utc")
    )

    if not fixture_id or kickoff is None:
        continue

    status = str(
        r.get("status") or ""
    ).strip().lower()

    source_status = str(
        r.get("source_status") or ""
    ).strip().upper()

    # Capture universe is prematch only.
    if status not in {
        "scheduled",
        "not started",
        "ns",
    } and source_status != "NS":
        continue

    if fixture_id in seen:
        continue

    seen.add(fixture_id)

    out.append({
        "forward_id":
            f"CAPTURE|{fixture_id}",

        "rule":
            "PBK16_CAPTURE",

        "status":
            "CAPTURE",

        "api_fixture_id":
            fixture_id,

        "match_date":
            kickoff.strftime("%Y-%m-%d"),

        "kickoff_time":
            kickoff.strftime("%H:%M"),

        "kickoff_utc":
            kickoff.isoformat(),

        "league":
            r.get("league_name") or "",

        "country":
            r.get("country") or "",

        "provider_league_id":
            r.get("provider_league_id") or "",

        "home_team":
            r.get("home_team") or "",

        "away_team":
            r.get("away_team") or "",

        "home_team_id":
            r.get("home_team_id") or "",

        "away_team_id":
            r.get("away_team_id") or "",

        "source_dataset":
            SOURCE_ID,

        "capture_authority":
            "PREMATCH_EVIDENCE_CAPTURE_ONLY",
    })


out.sort(
    key=lambda r: (
        r["kickoff_utc"],
        r["api_fixture_id"],
    )
)


with OUTPUT.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as fh:

    writer = csv.DictWriter(
        fh,
        fieldnames=FIELDS,
    )

    writer.writeheader()
    writer.writerows(out)


league_pairs = {
    (
        r["country"],
        r["league"],
    )
    for r in out
}


print("SOURCE ROWS:", len(rows))
print("CAPTURE ROWS:", len(out))
print("UNIQUE FIXTURES:", len(seen))
print("LEAGUE-COUNTRY PAIRS:", len(league_pairs))
print("OUTPUT:", OUTPUT)

print()
for country, league in sorted(league_pairs):
    n = sum(
        1
        for r in out
        if r["country"] == country
        and r["league"] == league
    )

    print(
        f"{country} | {league} | {n}"
    )
