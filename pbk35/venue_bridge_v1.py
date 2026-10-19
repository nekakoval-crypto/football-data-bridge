import argparse
import csv
import os
import tempfile
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SHADOW = Path(os.environ["PBK691_SHADOW"])
ROOT = Path(os.environ["PBK691_ROOT"])
OPS = ROOT / "PBK35_DATA" / "ops"

CALENDAR = OPS / "pbk16_capture_universe.csv"
VERIFIED = OPS / "pbk35_verified_venue_context_612.csv"
ROUND = SHADOW / "ops/current_round_fixtures.csv"
REGISTRY = SHADOW / "ops/pbk16_venue_registry.csv"

def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])

def norm(value):
    s = unicodedata.normalize(
        "NFKD", str(value or "").strip().casefold()
    )
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.split())

def utc(value):
    dt = datetime.fromisoformat(
        str(value or "").replace("Z", "+00:00")
    )
    if dt.tzinfo is None:
        raise ValueError("naive kickoff time")
    return dt.astimezone(timezone.utc)

def unique_index(rows, field):
    result = {}
    for r in rows:
        key = str(r.get(field) or "").strip()
        if not key or key in result:
            raise RuntimeError("duplicate/missing key: " + field)
        result[key] = r
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    calendar, _ = read(CALENDAR)
    verified, fields = read(VERIFIED)
    rounds, _ = read(ROUND)
    registry, _ = read(REGISTRY)

    if not {
        "api_fixture_id", "venue_city", "current_kickoff_utc"
    } <= set(fields):
        raise RuntimeError("VERIFIED_CONTEXT_SCHEMA_MISMATCH")

    current = unique_index(calendar, "api_fixture_id")
    prior = unique_index(verified, "api_fixture_id")

    # current_round can contain finished and cancelled matches:
    # only fixtures from the CAPTURE calendar are candidates.
    by_fixture = defaultdict(list)
    for row in rounds:
        key = str(row.get("fixture_id") or "").strip()
        if key:
            by_fixture[key].append(row)

    by_team = defaultdict(list)
    for row in registry:
        team = str(row.get("team_id") or "").strip()
        if team:
            by_team[team].append(row)

    additions = []
    blocked = []

    for fid, fixture in current.items():
        if fid in prior:
            continue

        candidates = [
            row for row in by_fixture.get(fid, [])
            if str(row.get("status") or "").strip().lower()
               == "scheduled"
        ]
        if len(candidates) != 1:
            blocked.append((fid, "CURRENT_FIXTURE_NOT_UNIQUE"))
            continue

        event = candidates[0]

        try:
            if utc(fixture["kickoff_utc"]) != utc(event["kickoff_utc"]):
                raise ValueError("KICKOFF_CONFLICT")
        except (ValueError, KeyError) as exc:
            blocked.append((fid, str(exc)))
            continue

        team = str(fixture.get("home_team_id") or "").strip()
        if team != str(event.get("home_team_id") or "").strip():
            blocked.append((fid, "HOME_TEAM_ID_CONFLICT"))
            continue

        if str(fixture.get("away_team_id") or "").strip() != str(
            event.get("away_team_id") or ""
        ).strip():
            blocked.append((fid, "AWAY_TEAM_ID_CONFLICT"))
            continue

        venue = norm(event.get("venue_name"))
        city = norm(event.get("venue_city"))

        if not venue or not city:
            blocked.append((fid, "FIXTURE_VENUE_OR_CITY_MISSING"))
            continue

        matching = [
            r for r in by_team.get(team, [])
            if norm(r.get("venue_name")) == venue
            and norm(r.get("venue_city")) == city
        ]

        if not matching:
            blocked.append((fid, "NO_EXACT_INDEPENDENT_VENUE"))
            continue

        # Multiple registry seasons are acceptable only if every
        # exact venue candidate identifies the same city.
        registry_cities = {
            norm(r.get("venue_city")) for r in matching
        }
        if registry_cities != {city}:
            blocked.append((fid, "VENUE_REGISTRY_CITY_CONFLICT"))
            continue

        additions.append({
            "api_fixture_id": fid,
            "venue_city": str(event["venue_city"]).strip(),
            "current_kickoff_utc": fixture["kickoff_utc"],
        })

    print("PBK691 VERIFIED VENUE BRIDGE")
    print("CURRENT FIXTURES =", len(current))
    print("EXISTING VERIFIED =", len(prior))
    print("NEW VERIFIED CANDIDATES =", len(additions))
    print("BLOCKED =", len(blocked))

    for row in additions[:15]:
        print(
            "VERIFIED =",
            row["api_fixture_id"],
            row["venue_city"],
        )
    for fid, reason in blocked[:20]:
        print("BLOCKED =", fid, reason)

    if not args.apply:
        print("DRY RUN = NO WRITES")
        return

    if not additions:
        print("NO NEW VERIFIED CONTEXT TO PUBLISH")
        return

    # Fail closed if the source changed during calculation.
    check_current, _ = read(CALENDAR)
    check_verified, _ = read(VERIFIED)
    if check_current != calendar or check_verified != verified:
        raise RuntimeError("INPUT_CHANGED_DURING_BRIDGE")

    fd, temp = tempfile.mkstemp(
        prefix="pbk691_", suffix=".tmp", dir=str(OPS)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=fields, extrasaction="raise"
            )
            writer.writeheader()
            writer.writerows(verified + additions)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, VERIFIED)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

    published, _ = read(VERIFIED)
    if len(published) != len(verified) + len(additions):
        raise RuntimeError("PUBLISHED_VENUE_COUNT_MISMATCH")

    print("VENUE CONTEXT PUBLISHED =", len(published))
    print("WEATHER AUTHORITY = UNCHANGED")
    print("BETTING AUTHORITY = NOT_AUTHORIZED")

if __name__ == "__main__":
    main()
