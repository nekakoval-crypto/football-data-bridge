"""PBK542: fail-closed match-bound city-level weather evidence admission.

This validates evidence and known city identities; it does not
establish stadium-level coordinates or predictive/betting authority.
"""
from datetime import datetime, timezone
import math

COUNTRIES = {
    "austria": "AT", "belgium": "BE", "denmark": "DK",
    "england": "GB", "france": "FR", "germany": "DE",
    "italy": "IT", "latvia": "LV", "lithuania": "LT",
    "netherlands": "NL", "norway": "NO", "poland": "PL",
    "portugal": "PT", "scotland": "GB", "spain": "ES",
    "turkey": "TR",
}

# Actual Open-Meteo city coordinates verified in PBK519/520/522.
VERIFIED_CITY_COORDS = {
    "1584432": ("TR", 40.54889, 34.95333),
    "1570415": ("ES", 43.37135, -8.39600),
    "1556681": ("GB", 56.39522, -3.43139),
    "1575187": ("DE", 50.11552, 8.68417),
    "1553197": ("PL", 50.06143, 19.93658),
    "1547639": ("LT", 55.73186, 24.35983),
    "1584430": ("TR", 37.91363, 40.21721),
}

ALLOWED_SNAPSHOTS = {"BASELINE", "T24", "T3", "T60"}

def _utc(value):
    try:
        result = datetime.fromisoformat(
            str(value or "").replace("Z", "+00:00")
        )
        return (
            result.astimezone(timezone.utc)
            if result.tzinfo is not None else None
        )
    except (ValueError, TypeError, OverflowError):
        return None

def valid_weather_evidence(row, fixture, context):
    """Return False unless the row belongs to this specific fixture."""
    if not row or not fixture or not context:
        return False

    fid = str(fixture.get("forward_id") or "").strip()
    fixture_id = str(fixture.get("api_fixture_id") or "").strip()
    if not fixture_id or fid != "CAPTURE|" + fixture_id:
        return False
    if str(row.get("forward_id") or "").strip() != fid:
        return False
    if str(row.get("api_fixture_id") or "").strip() != fixture_id:
        return False

    country = COUNTRIES.get(
        str(fixture.get("country") or "").strip().casefold()
    )
    if not country or str(row.get("country_code") or "").upper() != country:
        return False

    if not str(context.get("venue_city") or "").strip():
        return False
    if not str(row.get("venue_city") or "").strip():
        return False
    if not str(row.get("geocoded_name") or "").strip():
        return False
    if str(row.get("snapshot_type") or "") not in ALLOWED_SNAPSHOTS:
        return False

    kickoff = _utc(
        context.get("current_kickoff_utc")
        or fixture.get("kickoff_utc")
    )
    row_kickoff = _utc(row.get("kickoff_utc"))
    captured = _utc(row.get("captured_at_utc"))
    forecast = _utc(row.get("forecast_time_utc"))

    if not all((kickoff, row_kickoff, captured, forecast)):
        return False
    if row_kickoff != kickoff or not captured < kickoff:
        return False
    if row.get("evidence_time_status") != "PREMATCH_FROZEN":
        return False
    if str(row.get("usable_for_prematch") or "").lower() != "true":
        return False

    try:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        gap = float(row["forecast_gap_minutes"])
    except (KeyError, ValueError, TypeError):
        return False

    if not all(map(math.isfinite, (lat, lon, gap))):
        return False
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    if not (0 <= gap <= 90):
        return False
    actual_gap = abs((forecast-kickoff).total_seconds()) / 60
    if abs(actual_gap-gap) > 1:
        return False

    known = VERIFIED_CITY_COORDS.get(fixture_id)
    if known:
        expected_country, known_lat, known_lon = known
        if country != expected_country:
            return False
        if abs(lat-known_lat) > 0.02 or abs(lon-known_lon) > 0.02:
            return False

    # For other cities this is country-level plausibility,
    # not independently proven stadium geographic accuracy.
    return True
