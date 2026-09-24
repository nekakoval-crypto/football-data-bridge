import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "config" / "pbk_venue_evidence.csv"
OVERRIDES = ROOT / "config" / "pbk_venue_overrides.csv"

SHARED_IDS = {"907", "910", "176", "150", "2612", "22763"}
PROJECTABLE = {
    "roof_type",
    "roof_state_default",
    "enclosure_class",
    "wind_exposure_class",
    "acoustic_enclosure_class",
}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_shared_batch_evidence_contract():
    rows = read_csv(EVIDENCE)
    overrides = read_csv(OVERRIDES)

    ids = {r["venue_id"] for r in rows}
    assert SHARED_IDS <= ids

    assert all(r["source_url"].startswith("https://") for r in rows)
    assert all(r["evidence_status"] for r in rows)
    assert all(r["source_checked_at_utc"] for r in rows)

    projected = [
        r for r in rows
        if r["projection_allowed"].strip().lower() == "true"
    ]

    assert projected
    assert all(r["projection_field"] in PROJECTABLE for r in projected)
    assert all(r["captured_value"] not in {"", "UNKNOWN"} for r in projected)

    assert not any(
        r["projection_field"] in {"operational_capacity", "pitch_orientation_deg"}
        for r in projected
    )

    override_by_venue = {r["venue_id"]: r for r in overrides if r["venue_id"]}

    for r in projected:
        o = override_by_venue[r["venue_id"]]
        assert o[r["projection_field"]] == r["captured_value"]

    for venue_id in SHARED_IDS:
        o = override_by_venue.get(venue_id)
        if o:
            assert o["operational_capacity"] == ""
            assert o["pitch_orientation_deg"] == ""

    conflicts = {
        r["evidence_field"]
        for r in rows
        if r["evidence_status"] == "NEEDS_REVIEW"
    }
    assert "provider_capacity_conflict" in conflicts
    assert "surface_provider_conflict" in conflicts
