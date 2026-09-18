import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage80_fixture_history_archive as archive


def fixture(fid="100", observed="2026-09-15T15:17:00Z", status="scheduled", source="NS"):
    return {
        "fixture_id": fid,
        "provider_league_id": "39",
        "league_name": "Premier League",
        "country": "England",
        "season": "2026",
        "round": "Regular Season - 4",
        "kickoff_utc": "2026-09-18T19:00:00Z",
        "home_team": "Alpha",
        "away_team": "Beta",
        "referee": "A. Referee",
        "venue_name": "Test Stadium",
        "venue_city": "London",
        "status": status,
        "source_status": source,
        "score_home": "",
        "score_away": "",
        "observed_at_utc": observed,
    }


class Stage80FixtureHistoryArchiveTests(unittest.TestCase):
    def test_same_fixture_across_observation_runs_is_preserved(self):
        first = archive.append_observations([], [fixture()])
        second_row = fixture(observed="2026-09-15T23:17:00Z", status="finished", source="FT")
        second_row["score_home"] = "2"
        second_row["score_away"] = "1"
        second = archive.append_observations(first["rows"], [second_row])
        self.assertEqual(first["added_rows"], 1)
        self.assertEqual(second["added_rows"], 1)
        self.assertEqual(len(second["rows"]), 2)
        self.assertEqual({row["source_status"] for row in second["rows"]}, {"NS", "FT"})
        counts = archive.inventory(second["rows"])
        self.assertEqual(counts["unique_fixtures"], 1)
        self.assertEqual(counts["fixture_observations"], 2)
        self.assertEqual(counts["observation_runs"], 2)

    def test_rerun_same_snapshot_is_idempotent_and_existing_wins(self):
        first = archive.append_observations([], [fixture()])
        drift = fixture()
        drift["home_team"] = "Changed Name"
        second = archive.append_observations(first["rows"], [drift])
        self.assertEqual(second["added_rows"], 0)
        self.assertEqual(second["duplicate_current_rows"], 1)
        self.assertEqual(len(second["rows"]), 1)
        self.assertEqual(second["rows"][0]["home_team"], "Alpha")

    def test_invalid_identity_rows_are_rejected(self):
        missing_fixture = fixture(fid="")
        missing_observed = fixture(observed="")
        result = archive.append_observations([], [missing_fixture, missing_observed])
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["invalid_current_rows"], 2)

    def test_atomic_csv_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture_history_snapshots.csv"
            row = archive.normalize(fixture())
            archive.write_csv_atomic(path, archive.HISTORY_FIELDS, [row])
            loaded = archive.read_csv(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["fixture_id"], "100")
            self.assertEqual(loaded[0]["referee"], "A. Referee")
            self.assertEqual(loaded[0]["venue_name"], "Test Stadium")
            self.assertEqual(loaded[0]["venue_city"], "London")
            self.assertEqual(loaded[0]["archive_version"], archive.ARCHIVE_VERSION)
            self.assertFalse(path.with_suffix(".csv.tmp").exists())


if __name__ == "__main__":
    unittest.main()
