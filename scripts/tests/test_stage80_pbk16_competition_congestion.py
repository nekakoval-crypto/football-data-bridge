import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import stage80_pbk16_competition_congestion as s


def league_entry(pid, name, ptype, country, seasons):
    return {
        "league": {"id": pid, "name": name, "type": ptype},
        "country": {"name": country},
        "seasons": [{"year": year} for year in seasons],
    }


def fixture_payload(
    fid,
    league_id,
    league_name,
    country,
    season,
    kickoff,
    home_id,
    away_id,
    home_goals=1,
    away_goals=0,
    status="FT",
):
    return {
        "errors": [],
        "paging": {"current": 1, "total": 1},
        "response": [{
            "fixture": {
                "id": fid,
                "date": kickoff,
                "status": {"short": status},
                "venue": {"id": 10, "name": "Ground", "city": "City"},
            },
            "league": {
                "id": league_id,
                "name": league_name,
                "type": "League",
                "country": country,
                "season": season,
                "round": "Round 1",
            },
            "teams": {
                "home": {"id": home_id, "name": f"Team {home_id}"},
                "away": {"id": away_id, "name": f"Team {away_id}"},
            },
            "goals": {"home": home_goals, "away": away_goals},
        }],
    }


class PBK16CompetitionCongestionTests(unittest.TestCase):
    def test_real_config_targets_locked_16_leagues_and_expected_cup_slots(self):
        cfg = s.load_config()
        leagues = s.load_locked_leagues(cfg)
        self.assertEqual(len(leagues), 16)
        self.assertEqual({int(row["api_league_id"]) for row in leagues}, {
            39, 140, 135, 78, 61, 218, 144, 119,
            362, 365, 88, 103, 106, 94, 203, 179,
        })
        self.assertEqual(cfg["historical_seasons"], list(range(2017, 2026)))
        self.assertFalse(cfg["include_super_cups"])
        self.assertEqual(len(cfg["uefa_competitions"]), 3)
        self.assertEqual(len(cfg["domestic_cup_slots"]), 20)
        turkey = next(
            row for row in cfg["domestic_cup_slots"]
            if row["country"] == "Turkey" and row["slot"] == "NATIONAL_CUP"
        )
        self.assertIn("Türkiye Kupası", turkey["provider_name_aliases"])
        self.assertEqual(
            {(row["country"], row["slot"]) for row in cfg["domestic_cup_slots"] if row["country"] == "Portugal"},
            {("Portugal", "NATIONAL_CUP"), ("Portugal", "LEAGUE_CUP")},
        )
        self.assertEqual(
            {(row["country"], row["slot"]) for row in cfg["domestic_cup_slots"] if row["country"] == "Scotland"},
            {("Scotland", "NATIONAL_CUP"), ("Scotland", "LEAGUE_CUP")},
        )

    def test_discovery_resolves_by_provider_id_and_country_scoped_exact_alias(self):
        cfg = {
            "historical_seasons": [2024, 2025],
            "domestic_cup_slots": [{
                "country": "Netherlands",
                "slot": "NATIONAL_CUP",
                "canonical_name": "KNVB Beker",
                "provider_name_aliases": ["KNVB Beker"],
                "required": True,
            }],
            "uefa_competitions": [{
                "slot": "UCL",
                "provider_league_id": 2,
                "canonical_name": "UEFA Champions League",
                "provider_name_aliases": ["UEFA Champions League"],
                "seasons": [2024, 2025],
                "required": True,
            }],
            "discovery_endpoint": "/leagues",
        }
        locked = [{
            "country": "Netherlands",
            "league": "Eredivisie",
            "api_league_id": "88",
            "api_league_name": "Eredivisie",
        }]

        class Budget:
            def __call__(self, path, params, **kwargs):
                if params.get("country") == "Netherlands":
                    return {
                        "errors": [],
                        "paging": {"current": 1, "total": 1},
                        "response": [
                            league_entry(88, "Eredivisie", "League", "Netherlands", [2024, 2025]),
                            league_entry(90, "KNVB Beker", "Cup", "Netherlands", [2024, 2025]),
                            league_entry(999, "Super Cup", "Cup", "Netherlands", [2024, 2025]),
                        ],
                    }
                if params.get("id") == 2:
                    return {
                        "errors": [],
                        "paging": {"current": 1, "total": 1},
                        "response": [
                            league_entry(2, "UEFA Champions League", "Cup", "World", [2024, 2025]),
                        ],
                    }
                raise AssertionError(params)

        catalog, warnings = s.discover_catalog(cfg, locked, Budget())
        self.assertEqual(warnings, [])
        self.assertEqual(len(catalog), 3)
        self.assertEqual(
            {(row["competition_role"], row["provider_league_id"]) for row in catalog},
            {("DOMESTIC_LEAGUE", "88"), ("DOMESTIC_CUP", "90"), ("UEFA", "2")},
        )
        self.assertNotIn("999", {row["provider_league_id"] for row in catalog})
        self.assertTrue(all(row["discovery_status"] == "RESOLVED" for row in catalog))

    def test_state_marks_provider_unavailable_season_terminal_without_api_attempt(self):
        specs = [{
            "competition_role": "DOMESTIC_CUP",
            "country": "France",
            "slot": "LEAGUE_CUP",
            "provider_competition_id": 65,
            "competition_name": "Coupe de la Ligue",
            "season": 2020,
            "provider_season_available": False,
        }]
        state = s.state_rows_for_specs(specs, [])
        self.assertEqual(state[0]["status"], "UNAVAILABLE_PROVIDER_SEASON")
        self.assertEqual(state[0]["provider_season_available"], "false")

    def test_payload_rejects_pagination_instead_of_silent_partial_capture(self):
        payload = {"errors": [], "paging": {"current": 1, "total": 2}, "response": []}
        with self.assertRaisesRegex(RuntimeError, "paginated"):
            s.payload_response(payload)

    def test_normalize_preserves_governance_and_provider_identity(self):
        spec = {
            "competition_role": "DOMESTIC_LEAGUE",
            "country": "England",
            "slot": "LEAGUE",
            "provider_competition_id": 39,
            "competition_name": "Premier League",
            "season": 2025,
        }
        payload = fixture_payload(
            101, 39, "Premier League", "England", 2025,
            "2025-08-10T15:00:00+00:00", 1, 2, 2, 1,
        )
        provider_rows, rows = s.normalize_fixture_payload(
            payload, spec, "2026-09-19T08:00:00Z"
        )
        self.assertEqual(provider_rows, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["result"], "H")
        self.assertEqual(rows[0]["competition_role"], "DOMESTIC_LEAGUE")
        self.assertEqual(rows[0]["research_only"], "true")
        self.assertEqual(rows[0]["operational_betting_authority"], "false")
        self.assertEqual(rows[0]["forward_journal_mutation"], "false")

    def test_congestion_uses_only_strictly_prior_played_nonleague_fixtures(self):
        governance = {
            "historical_backfill_only": "true",
            "research_only": "true",
            "operational_betting_authority": "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        }
        domestic = {
            "fixture_id": "500",
            "competition_role": "DOMESTIC_LEAGUE",
            "country": "England",
            "slot": "LEAGUE",
            "provider_competition_id": "39",
            "competition_name": "Premier League",
            "season": "2025",
            "round": "Round 2",
            "kickoff_utc": "2025-09-14T15:00:00+00:00",
            "status": "FT",
            "home_team_id": "10",
            "home_team": "Home",
            "away_team_id": "20",
            "away_team": "Away",
            **governance,
        }
        thursday_uefa = {
            "fixture_id": "400",
            "competition_role": "UEFA",
            "country": "World",
            "slot": "UEL",
            "provider_competition_id": "3",
            "competition_name": "UEFA Europa League",
            "season": "2025",
            "round": "League Stage",
            "kickoff_utc": "2025-09-11T19:00:00+00:00",
            "status": "FT",
            "home_team_id": "10",
            "home_team": "Home",
            "away_team_id": "99",
            "away_team": "Other",
            "home_goals": "1",
            "away_goals": "0",
            "result": "H",
            **governance,
        }
        future_cup = {
            "fixture_id": "600",
            "competition_role": "DOMESTIC_CUP",
            "country": "England",
            "slot": "NATIONAL_CUP",
            "provider_competition_id": "45",
            "competition_name": "FA Cup",
            "season": "2025",
            "round": "Round 3",
            "kickoff_utc": "2025-09-20T15:00:00+00:00",
            "status": "FT",
            "home_team_id": "10",
            "home_team": "Home",
            "away_team_id": "88",
            "away_team": "Future",
            "home_goals": "1",
            "away_goals": "0",
            "result": "H",
            **governance,
        }
        postponed_prior = {
            "fixture_id": "401",
            "competition_role": "DOMESTIC_CUP",
            "country": "England",
            "slot": "LEAGUE_CUP",
            "provider_competition_id": "48",
            "competition_name": "League Cup",
            "season": "2025",
            "round": "Round 1",
            "kickoff_utc": "2025-09-12T19:00:00+00:00",
            "status": "PST",
            "home_team_id": "20",
            "home_team": "Away",
            "away_team_id": "77",
            "away_team": "Other",
            **governance,
        }

        domestic_rows, out, invalid = s.build_congestion(
            [domestic, thursday_uefa, future_cup, postponed_prior]
        )
        self.assertEqual(len(domestic_rows), 1)
        self.assertEqual(invalid, 0)
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertEqual(row["home_prev_nonleague_fixture_id"], "400")
        self.assertEqual(row["home_prev_nonleague_was_uefa"], "true")
        self.assertEqual(row["home_prev_nonleague_was_thursday"], "true")
        self.assertEqual(row["either_team_prev_uefa_within_96h"], "true")
        self.assertEqual(row["away_prev_nonleague_fixture_id"], "")
        self.assertEqual(row["future_schedule_used"], "false")
        self.assertEqual(row["no_lookahead"], "true")

    def test_run_resumes_captured_fixture_cells(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = {
                "historical_seasons": [2025] * 9,
                "required_league_count": 16,
                "domestic_cup_slots": [],
                "uefa_competitions": [],
                "discovery_endpoint": "/leagues",
                "fixture_endpoint": "/fixtures",
            }
            locked = [{
                "country": "England",
                "league": "Premier League",
                "api_league_id": "39",
                "api_league_name": "Premier League",
            }]
            calls = []

            def fake_get(path, params=None, **kwargs):
                calls.append((path, dict(params or {})))
                if path == "/leagues":
                    return {
                        "errors": [],
                        "paging": {"current": 1, "total": 1},
                        "response": [
                            league_entry(39, "Premier League", "League", "England", [2025]),
                        ],
                    }
                if path == "/fixtures":
                    return fixture_payload(
                        1, 39, "Premier League", "England", 2025,
                        "2025-08-10T15:00:00+00:00", 10, 20,
                    )
                raise AssertionError(path)

            paths = {
                "COMPETITION_CATALOG": root / "catalog.csv",
                "ARCHIVE": root / "archive.csv",
                "QUERY_STATE": root / "state.csv",
                "META": root / "meta.json",
                "CONGESTION": root / "congestion.csv",
                "CONGESTION_META": root / "congestion_meta.json",
                "SHARED_STATE": root / "shared.json",
            }
            with patch.object(s, "load_config", return_value=cfg),                  patch.object(s, "load_locked_leagues", return_value=locked),                  patch.multiple(s, **paths):
                meta1, _ = s.run(
                    get=fake_get,
                    now=datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc),
                )
                fixture_calls_1 = sum(path == "/fixtures" for path, _ in calls)
                self.assertEqual(meta1["captured_fixture_cells"], 1)
                self.assertEqual(fixture_calls_1, 1)

                meta2, _ = s.run(
                    get=fake_get,
                    now=datetime(2026, 9, 19, 8, 5, tzinfo=timezone.utc),
                )
                fixture_calls_2 = sum(path == "/fixtures" for path, _ in calls)
                self.assertEqual(meta2["captured_fixture_cells"], 1)
                self.assertEqual(fixture_calls_2, 1)

                with (root / "archive.csv").open(encoding="utf-8-sig", newline="") as handle:
                    archive = list(csv.DictReader(handle))
                self.assertEqual(len(archive), 1)


if __name__ == "__main__":
    unittest.main()
