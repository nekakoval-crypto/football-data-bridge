import unittest

from scripts.stage84_team_style_metric_observations import flatten_profiles


class Stage84MetricObservationsTests(unittest.TestCase):
    def test_preserves_league_season_provenance_from_stage83_profile(self):
        payload = {
            "version": "PBK_STAGE83_TEAM_STYLE_OPERATIONAL_PROFILES_V1",
            "before_utc": "2026-09-01T00:00:00+00:00",
            "teams": {
                "77": {
                    "team_id": "77",
                    "team_name": "Provenance FC",
                    "league_id": "140",
                    "league_name": "La Liga",
                    "season": "2026",
                    "profile": {
                        "splits": {
                            "Overall": {
                                "windows": {
                                    "5": {
                                        "actual_matches": 5,
                                        "window_complete": True,
                                        "metrics": {
                                            "shots_for": {
                                                "status": "KNOWN",
                                                "mean": 12.4,
                                                "sample_size": 5,
                                                "coverage": 1.0,
                                            }
                                        },
                                    }
                                }
                            }
                        }
                    },
                }
            },
        }

        rows = flatten_profiles(payload)

        self.assertEqual(len(rows), 1)

        row = rows[0]

        self.assertEqual(row["team_id"], "77")
        self.assertEqual(row["team_name"], "Provenance FC")
        self.assertEqual(row["league_id"], "140")
        self.assertEqual(row["league_name"], "La Liga")
        self.assertEqual(row["season"], "2026")
        self.assertEqual(row["split"], "overall")
        self.assertEqual(row["window"], 5)
        self.assertEqual(row["metric"], "shots_for")
        self.assertEqual(row["value"], 12.4)
        self.assertIsNone(row["style_dimension_value"])


if __name__ == "__main__":
    unittest.main()