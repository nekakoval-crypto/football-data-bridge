import csv
import hashlib
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(os.environ.get("PBK35_ROOT", Path(__file__).resolve().parent))
SOURCE = Path(os.environ["PBK683_SOURCE"])
DEST = ROOT / "PBK35_DATA/ops/pbk16_capture_universe.csv"
ARCHIVE = ROOT / "PBK35_DATA/ops/weather_snapshots.csv"

def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])

def utc(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("kickoff timezone missing")
    return dt.astimezone(timezone.utc)

def validate(rows, fields):
    required = {
        "forward_id", "api_fixture_id", "kickoff_utc",
        "home_team", "away_team", "country", "status"
    }
    if not required <= set(fields):
        raise RuntimeError("calendar schema mismatch")

    seen = set()
    for row in rows:
        fid = str(row["api_fixture_id"]).strip()
        if not fid or fid in seen:
            raise RuntimeError("empty or duplicate fixture identity")
        seen.add(fid)

        if str(row["forward_id"]).strip() != "CAPTURE|" + fid:
            raise RuntimeError("forward fixture identity mismatch")

        if row["status"] != "CAPTURE":
            raise RuntimeError("unexpected fixture status")

        if not row["home_team"] or not row["away_team"] or not row["country"]:
            raise RuntimeError("incomplete fixture identity")

        utc(row["kickoff_utc"])

    if not rows:
        raise RuntimeError("empty calendar prohibited")

    return seen

def main():
    source, source_fields = read(SOURCE)
    previous, previous_fields = read(DEST)
    archive, _ = read(ARCHIVE)

    current_ids = validate(source, source_fields)
    prior_ids = validate(previous, previous_fields)

    # The latest upstream calendar can add/remove matches, but
    # weather evidence remains historical and is not discarded.
    print("UPSTREAM FIXTURES =", len(source))
    print("DESKTOP FIXTURES =", len(previous))
    print("WEATHER ARCHIVE ROWS =", len(archive))
    print("NEW FIXTURES =", len(current_ids - prior_ids))
    print("NO LONGER CURRENT =", len(prior_ids - current_ids))

    if source_fields != previous_fields:
        raise RuntimeError("calendar columns changed")

    # Match content is compared by fixture ID, independent of CSV row order.
    old_by_id = {r["api_fixture_id"]: r for r in previous}
    new_by_id = {r["api_fixture_id"]: r for r in source}

    if old_by_id == new_by_id:
        print("CALENDAR = ALREADY SYNCHRONIZED")
        return

    if "--apply" not in sys.argv:
        print("CALENDAR = CHANGES DETECTED (DRY RUN)")
        return

    dest_dir = DEST.parent
    fd, temporary = tempfile.mkstemp(
        dir=str(dest_dir), prefix="pbk683_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=source_fields)
            writer.writeheader()
            writer.writerows(source)
            f.flush()
            os.fsync(f.fileno())

        # Preserve every published calendar version as an immutable backup.
        digest = hashlib.sha256(DEST.read_bytes()).hexdigest()[:16]
        previous_copy = (
            ROOT / "PBK35_DATA/backups" /
            f"calendar_before_{digest}.csv"
        )
        previous_copy.parent.mkdir(parents=True, exist_ok=True)
        if not previous_copy.exists():
            previous_copy.write_bytes(DEST.read_bytes())

        os.replace(temporary, DEST)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    after, after_fields = read(DEST)
    if validate(after, after_fields) != current_ids:
        raise RuntimeError("published calendar failed verification")

    print("CALENDAR = SYNCHRONIZED")
    print("FIXTURES =", len(after))
    print("WEATHER ARCHIVE = PRESERVED")

if __name__ == "__main__":
    main()
