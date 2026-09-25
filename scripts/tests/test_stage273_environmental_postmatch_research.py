import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts import stage273_environmental_postmatch_research as m


# Stage273 regression coverage for current Stage80 canonical fixture schema.
class EnvironmentalPostmatchResearchTests(unittest.TestCase):

    def test_contract_explicitly_denies_prematch_semantics(self):
        cfg = json.loads(
            Path("config/pbk_environmental_postmatch_research_v1.json")
            .read_text(encoding="utf-8")
        )
        m.validate_contract(cfg)
        source = cfg["source_policy"]
        self.assertFalse(source["historical_proxy_is_direct_stadium_observation"])
        self.assertFalse(source["historical_proxy_is_prematch_forecast"])
        self.assertFalse(source["usable_for_prematch"])

    def test_match_window_weather_summary(self):
        hourly = {
            "time": [
                "2026-09-24T18:00",
                "2026-09-24T19:00",
                "2026-09-24T20:00",
                "2026-09-24T21:00",
                "2026-09-24T22:00",
            ],
            "temperature_2m": [20, 19, 18, 17, 16],
            "apparent_temperature": [20, 18, 17, 16, 15],
            "relative_humidity_2m": [60, 70, 80, 90, 95],
            "dew_point_2m": [12, 13, 14, 15, 15],
            "surface_pressure": [1000, 1001, 1002, 1003, 1004],
            "precipitation": [0, 1, 3, 2, 0],
            "rain": [0, 1, 3, 2, 0],
            "showers": [0, 0, 0, 0, 0],
            "snowfall": [0, 0, 0, 0, 0],
            "weather_code": [3, 61, 63, 61, 3],
            "visibility": [10000, 8000, 5000, 7000, 10000],
            "wind_speed_10m": [10, 15, 20, 25, 10],
            "wind_gusts_10m": [20, 30, 40, 45, 20],
            "wind_direction_10m": [180, 180, 190, 200, 200],
        }
        start = datetime(2026, 9, 24, 18, 30, tzinfo=timezone.utc)
        end = datetime(2026, 9, 24, 21, 30, tzinfo=timezone.utc)

        row = m.summarize_historical_weather(hourly, start, end)

        self.assertIsNotNone(row)
        self.assertEqual(row["hourly_points"], "3")
        self.assertEqual(row["precipitation_sum_mm"], "6")
        self.assertEqual(row["rain_sum_mm"], "6")
        self.assertEqual(row["wind_gust_max_kmh"], "45")
        self.assertEqual(row["visibility_min_m"], "5000")
        self.assertEqual(row["weather_code_mode"], "61")

    def test_circular_wind_mean_handles_north_wrap(self):
        value = m.circular_mean_degrees([350.0, 10.0])
        self.assertIsNotNone(value)
        self.assertTrue(value < 1.0 or value > 359.0)

    def test_http_json_retries_transient_failure(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"ok": true}'

        calls=[]

        def fake_urlopen(request, timeout):
            calls.append(timeout)
            if len(calls) < 3:
                raise TimeoutError("transient")
            return FakeResponse()

        with mock.patch.object(
            m.urllib.request,
            "urlopen",
            side_effect=fake_urlopen,
        ):
            with mock.patch.object(m.time, "sleep") as sleep:
                payload=m.http_json(
                    "https://example.test/weather",
                    {"a":"b"},
                    attempts=3,
                    retry_delay=0.1,
                )

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleep.call_count, 2)

    def test_http_json_fails_after_bound(self):
        with mock.patch.object(
            m.urllib.request,
            "urlopen",
            side_effect=TimeoutError("persistent"),
        ) as urlopen:
            with mock.patch.object(m.time, "sleep"):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "failed after 2 attempts",
                ):
                    m.http_json(
                        "https://example.test/weather",
                        {},
                        attempts=2,
                        retry_delay=0,
                    )

        self.assertEqual(urlopen.call_count, 2)

    def test_city_query_variants_clean_region_suffix_and_alias(self):
        self.assertEqual(
            m.city_query_variants("Bournemouth, Dorset")[:2],
            ["Bournemouth, Dorset", "Bournemouth"],
        )
        self.assertIn("Vienna", m.city_query_variants("Wien"))
        self.assertIn("Rome", m.city_query_variants("Roma"))

    def test_normalize_place_transliterates_non_ascii_letters(self):
        self.assertEqual(m.normalize_place("Łódź"), "lodz")
        self.assertEqual(m.normalize_place("Nørre Lyngby"), "norre lyngby")

    def test_city_query_variants_add_locality_aliases(self):
        self.assertIn("Kongens Lyngby", m.city_query_variants("Lyngby"))
        self.assertIn("Turin", m.city_query_variants("Torino"))
        self.assertIn("Venice", m.city_query_variants("Venezia"))

    def test_candidate_selection_prefers_major_lodz(self):
        venue={"team_country":"Poland","venue_city":"Łódź"}
        queries=m.city_query_variants("Łódź")
        candidates=[
            {"name":"Łódź","country":"Poland","country_code":"PL","latitude":52.255,"longitude":16.742,"population":0,"feature_code":"PPL"},
            {"name":"Lodz","country":"Poland","country_code":"PL","latitude":51.759,"longitude":19.456,"population":650000,"feature_code":"PPLA"},
        ]
        result,quality=m.select_geocode_candidate(candidates,venue,queries)
        self.assertEqual(result["feature_code"],"PPLA")
        self.assertGreater(float(result["population"]),100000)
        self.assertEqual(quality,3)

    def test_candidate_selection_prefers_canonical_locality_aliases(self):
        cases=[
            ("Lyngby","Kongens Lyngby","Denmark","DK",55.77,12.50),
            ("Villarreal","Vila-real","Spain","ES",39.94,-0.10),
            ("Kocaeli","Izmit","Turkey","TR",40.77,29.92),
            ("Torino","Turin","Italy","IT",45.07,7.69),
            ("Venezia","Venice","Italy","IT",45.44,12.33),
        ]
        for venue_city,major_name,country,code,lat,lon in cases:
            with self.subTest(venue_city=venue_city):
                venue={"team_country":country,"venue_city":venue_city}
                queries=m.city_query_variants(venue_city)
                candidates=[
                    {"name":venue_city,"country":country,"country_code":code,"latitude":57.0,"longitude":9.0,"population":10,"feature_code":"PPL"},
                    {"name":major_name,"country":country,"country_code":code,"latitude":lat,"longitude":lon,"population":50000,"feature_code":"PPLA"},
                ]
                result,quality=m.select_geocode_candidate(candidates,venue,queries)
                self.assertEqual(result["name"],major_name)
                self.assertEqual(quality,3)

    def test_candidate_selection_prefers_turin_and_venice_aliases(self):
        cases=[
            ("Torino","Turin",45.07,7.69),
            ("Venezia","Venice",45.44,12.33),
        ]
        for venue_city,major_name,lat,lon in cases:
            with self.subTest(venue_city=venue_city):
                venue={"team_country":"Italy","venue_city":venue_city}
                queries=m.city_query_variants(venue_city)
                candidates=[
                    {"name":venue_city,"country":"Italy","country_code":"IT","latitude":44.889,"longitude":11.991,"population":14,"feature_code":"PPL"},
                    {"name":major_name,"country":"Italy","country_code":"IT","latitude":lat,"longitude":lon,"population":250000,"feature_code":"PPLA"},
                ]
                result,quality=m.select_geocode_candidate(candidates,venue,queries)
                self.assertEqual(result["name"],major_name)
                self.assertEqual(quality,3)

    def test_candidate_country_filter_maps_scotland_to_gb(self):
        venue={"team_country":"Scotland"}
        self.assertTrue(
            m.candidate_country_ok(
                {"country_code":"GB","country":"United Kingdom"},
                venue,
            )
        )
        self.assertFalse(
            m.candidate_country_ok(
                {"country_code":"US","country":"United States"},
                venue,
            )
        )

    def test_candidate_selection_prefers_real_major_rome(self):
        venue={
            "team_country":"Italy",
            "venue_city":"Roma",
        }
        queries=m.city_query_variants("Roma")
        candidates=[
            {
                "name":"Roma",
                "country":"Italy",
                "country_code":"IT",
                "latitude":44.994,
                "longitude":11.106,
                "population":150,
                "feature_code":"PPL",
            },
            {
                "name":"Rome",
                "country":"Italy",
                "country_code":"IT",
                "latitude":41.8919,
                "longitude":12.5113,
                "population":2318895,
                "feature_code":"PPLC",
            },
        ]
        result,quality=m.select_geocode_candidate(
            candidates,
            venue,
            queries,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["feature_code"],"PPLC")
        self.assertEqual(quality,3)

    def test_wienau_is_not_accepted_for_wien_when_vienna_exists(self):
        venue={
            "team_country":"Austria",
            "venue_city":"Wien",
        }
        queries=m.city_query_variants("Wien")
        candidates=[
            {
                "name":"Wienau",
                "country":"Austria",
                "country_code":"AT",
                "latitude":48.5,
                "longitude":14.7,
                "population":100,
                "feature_code":"PPL",
            },
            {
                "name":"Vienna",
                "country":"Austria",
                "country_code":"AT",
                "latitude":48.208,
                "longitude":16.373,
                "population":1973403,
                "feature_code":"PPLC",
            },
        ]
        result,quality=m.select_geocode_candidate(
            candidates,
            venue,
            queries,
        )
        self.assertEqual(result["name"],"Vienna")
        self.assertEqual(quality,3)

    def test_unresolved_v2_is_cached_and_skippable(self):
        venue={
            "venue_id":"123",
            "venue_name":"Example",
            "venue_city":"Unknownville",
            "team_country":"Germany",
        }
        row=m.unresolved_geocode_record(
            venue,
            datetime(2026,9,24,tzinfo=timezone.utc),
            ["Unknownville"],
        )
        self.assertEqual(row["geocode_quality_status"],"UNRESOLVED_V4")
        self.assertEqual(row["resolver_version"],m.GEOCODE_RESOLVER_VERSION)
        self.assertEqual(
            m.unresolved_geocache_venue_ids([row]),
            {"123"},
        )
        self.assertEqual(m.verified_geocache_by_venue([row]),{})

    def test_snapshot_geocode_drift_detects_bad_city_proxy(self):
        snapshot={"latitude":"44.994","longitude":"11.106"}
        geo={"latitude":"41.8919","longitude":"12.5113"}
        drift=m.snapshot_geocode_drift_km(snapshot,geo)
        self.assertIsNotNone(drift)
        self.assertGreater(drift,m.GEOCODE_REPAIR_DISTANCE_KM)

    def test_snapshot_geocode_drift_accepts_same_city_area(self):
        snapshot={"latitude":"41.389","longitude":"2.159"}
        geo={"latitude":"41.387","longitude":"2.17"}
        drift=m.snapshot_geocode_drift_km(snapshot,geo)
        self.assertIsNotNone(drift)
        self.assertLess(drift,m.GEOCODE_REPAIR_DISTANCE_KM)

    def test_stale_snapshot_version_is_detectable_for_current_cache_sync(self):
        snapshot={
            "geocode_resolver_version":"PBK_GEOCODE_V3",
            "latitude":"45.070",
            "longitude":"7.687",
        }
        geo={
            "resolver_version":"PBK_GEOCODE_V4",
            "latitude":"45.070",
            "longitude":"7.687",
        }
        self.assertNotEqual(
            snapshot["geocode_resolver_version"],
            m.GEOCODE_RESOLVER_VERSION,
        )
        drift=m.snapshot_geocode_drift_km(snapshot,geo)
        self.assertIsNotNone(drift)
        self.assertLessEqual(drift,m.GEOCODE_REPAIR_DISTANCE_KM)

    def test_propagate_snapshot_geocode_metadata_preserves_weather(self):
        snapshot={
            "fixture_id":"1",
            "latitude":"41.389",
            "longitude":"2.159",
            "geocode_quality_status":"VERIFIED_LOCALITY_V3",
            "geocode_resolver_version":"PBK_GEOCODE_V3",
            "temperature_mean_c":"21.5",
            "captured_at_utc":"2026-09-24T10:00:00Z",
        }
        geo={
            "latitude":"41.387",
            "longitude":"2.17",
            "geocode_quality_status":"VERIFIED_LOCALITY_V4",
            "resolver_version":"PBK_GEOCODE_V4",
        }
        row=m.propagate_snapshot_geocode_metadata(snapshot,geo)
        self.assertEqual(row["geocode_quality_status"],"VERIFIED_LOCALITY_V4")
        self.assertEqual(row["geocode_resolver_version"],"PBK_GEOCODE_V4")
        self.assertEqual(row["latitude"],"41.387")
        self.assertEqual(row["longitude"],"2.17")
        self.assertEqual(row["temperature_mean_c"],"21.5")
        self.assertEqual(row["captured_at_utc"],"2026-09-24T10:00:00Z")

    def test_finished_bridge_fixtures_accepts_only_trusted_identity(self):
        rows=[
            {
                "api_fixture_id":"9001",
                "provider_league_id":"39",
                "league_code":"E0",
                "season_start":"2024",
                "api_kickoff_utc":"2024-08-17T14:00:00Z",
                "api_home_team":"Home FC",
                "api_away_team":"Away FC",
                "api_home_goals":"2",
                "api_away_goals":"1",
                "mapping_status":"AUTO",
                "one_to_one_verified":"true",
                "fuzzy_string_matching_used":"false",
            },
            {
                "api_fixture_id":"9002",
                "api_kickoff_utc":"2024-08-17T14:00:00Z",
                "mapping_status":"REVIEW",
                "one_to_one_verified":"false",
                "fuzzy_string_matching_used":"false",
            },
        ]
        result=m.finished_bridge_fixtures(rows)
        self.assertEqual(set(result),{"9001"})
        self.assertEqual(result["9001"]["home_goals"],"2")
        self.assertEqual(result["9001"]["round"],"HISTORICAL_BRIDGE")

    def test_finished_fixture_filter_rejects_scheduled(self):
        rows = [
            {
                "fixture_id": "1",
                "is_finished": "YES",
                "source_status": "FT",
                "kickoff_utc": "2026-09-20T15:00:00Z",
            },
            {
                "fixture_id": "2",
                "is_finished": "NO",
                "source_status": "NS",
                "kickoff_utc": "2026-10-10T15:00:00Z",
            },
        ]
        result = m.finished_fixtures(rows)
        self.assertEqual(set(result), {"1"})

    def test_current_stage80_historical_fixture_schema_is_normalized(self):
        rows = [{
            "fixture_id": "1494764",
            "provider_league_id": "103",
            "league_name": "Eliteserien",
            "season": "2026",
            "round": "Regular Season - 22",
            "home_team": "Brann",
            "away_team": "Bodo/Glimt",
            "latest_kickoff_utc": "2026-09-20T17:15:00+00:00",
            "latest_status": "finished",
            "latest_source_status": "FT",
            "terminal_observed": "YES",
            "final_score_home": "2",
            "final_score_away": "1",
        }]

        result = m.finished_fixtures(rows)

        self.assertEqual(set(result), {"1494764"})
        row = result["1494764"]
        self.assertEqual(row["kickoff_utc"], "2026-09-20T17:15:00+00:00")
        self.assertEqual(row["source_status"], "FT")
        self.assertEqual(row["home_goals"], "2")
        self.assertEqual(row["away_goals"], "1")

    def test_team_statistics_require_both_sides(self):
        rows = [
            {"fixture_id": "1", "side": "HOME", "team_id": "10"},
            {"fixture_id": "1", "side": "AWAY", "team_id": "20"},
            {"fixture_id": "2", "side": "HOME", "team_id": "30"},
        ]
        result = m.complete_team_stats(rows)
        self.assertEqual(set(result), {"1"})

    def test_mechanism_projection_uses_real_match_statistics(self):
        snapshots = [{
            "fixture_id": "1",
            "source_class": "HISTORICAL_FORECAST_ASSIMILATION_PROXY",
            "temperature_mean_c": "15",
            "rain_sum_mm": "8",
            "precipitation_sum_mm": "8",
            "wind_gust_max_kmh": "42",
            "visibility_min_m": "6000",
        }]
        stats = {
            "1": [
                {
                    "fixture_id": "1",
                    "side": "HOME",
                    "team_id": "10",
                    "shots_total": "20",
                    "shots_on_goal": "8",
                    "shots_outsidebox": "7",
                    "goalkeeper_saves": "3",
                    "corners": "6",
                    "passes_accuracy_pct": "80",
                    "expected_goals": "2.1",
                },
                {
                    "fixture_id": "1",
                    "side": "AWAY",
                    "team_id": "20",
                    "shots_total": "10",
                    "shots_on_goal": "5",
                    "shots_outsidebox": "5",
                    "goalkeeper_saves": "4",
                    "corners": "4",
                    "passes_accuracy_pct": "70",
                    "expected_goals": "1.4",
                },
            ]
        }
        fixtures = {
            "1": {
                "fixture_id": "1",
                "provider_league_id": "39",
                "league_name": "Premier League",
                "season": "2026",
                "round": "R1",
                "kickoff_utc": "2026-09-20T15:00:00Z",
                "home_team": "Home",
                "away_team": "Away",
                "home_goals": "4",
                "away_goals": "3",
            }
        }
        venues = {
            "10": {
                "venue_id": "100",
                "venue_name": "Example",
                "surface_provider": "grass",
                "roof_type": "UNKNOWN",
            }
        }
        events = [
            {"fixture_id": "1", "event_type": "Goal", "detail": "Normal Goal"},
            {"fixture_id": "1", "event_type": "Goal", "detail": "Penalty"},
            {"fixture_id": "1", "event_type": "Var", "detail": "Goal cancelled"},
        ]

        rows = m.mechanism_projection(snapshots, stats, fixtures, venues, events)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["goals_total"], "7")
        self.assertEqual(row["shots_total"], "30")
        self.assertEqual(row["shots_outsidebox_total"], "12")
        self.assertEqual(row["goalkeeper_saves_total"], "7")
        self.assertEqual(row["corners_total"], "10")
        self.assertEqual(row["passes_accuracy_mean"], "75")
        self.assertEqual(row["expected_goals_total"], "3.5")
        self.assertEqual(row["normal_goals"], "1")
        self.assertEqual(row["penalty_goals"], "1")
        self.assertEqual(row["var_events"], "1")
        self.assertEqual(
            row["goalkeeper_error_evidence"],
            "NOT_AVAILABLE_IN_CURRENT_EVENT_ARCHIVE",
        )
        self.assertEqual(row["causal_claim_authorized"], "false")
        self.assertEqual(row["environment_usable_for_prematch"], "false")
        self.assertEqual(row["predictive_authority"], "NOT_AUTHORIZED")

    def test_single_match_never_authorizes_causal_claim(self):
        self.assertIn("causal_claim_authorized", m.DATASET_FIELDS)
        self.assertNotIn("environment_score", m.DATASET_FIELDS)


if __name__ == "__main__":
    unittest.main()
