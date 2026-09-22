import unittest

from scripts import pbk16_motivation_objective_contracts as c


def row(country,league_id,league_name,season):
    return {
        "country":country,
        "provider_league_id":str(league_id),
        "league_name":league_name,
        "season":str(season),
    }


class PBK16MotivationObjectiveContractsTests(unittest.TestCase):
    def test_existing_top5_contracts_are_reused_not_duplicated(self):
        item=c.cell_contract(row("England",39,"Premier League",2024))
        self.assertEqual(item["status"],"VERIFIED")
        self.assertEqual(item["source_contract"],"HISTORICAL_TOP5_FORMATS")
        self.assertTrue(item["title_boundary_authorized"])
        self.assertTrue(item["relegation_boundary_authorized"])
        self.assertEqual(item["direct_relegation_start_rank"],18)

    def test_historical_pbk16_batch_a(self):
        cases = [
            (
                row("Norway",103,"Eliteserien",2019),
                30,
                13,
                15,
                14,
            ),
            (
                row("Poland",106,"Ekstraklasa",2020),
                30,
                15,
                16,
                None,
            ),
            (
                row("Turkey",203,"Super Lig",2020),
                40,
                17,
                18,
                None,
            ),
        ]

        for payload, total_games, safe_rank, direct_start, playoff in cases:
            with self.subTest(payload=payload):
                item = c.cell_contract(payload)

                self.assertEqual(item["status"], "VERIFIED")
                self.assertEqual(
                    item["source_contract"],
                    "HISTORICAL_PBK16_FORMATS",
                )
                self.assertTrue(item["title_boundary_authorized"])
                self.assertTrue(item["relegation_boundary_authorized"])
                self.assertEqual(item["total_games"], total_games)
                self.assertEqual(item["safe_rank"], safe_rank)
                self.assertEqual(
                    item["direct_relegation_start_rank"],
                    direct_start,
                )
                self.assertEqual(
                    item["relegation_playoff_rank"],
                    playoff,
                )



    def test_historical_pbk16_batch_b(self):
        cases = [
            (
                row("Poland",106,"Ekstraklasa",2022),
                34,
                15,
                16,
            ),
            (
                row("Turkey",203,"Super Lig",2021),
                38,
                16,
                17,
            ),
            (
                row("Turkey",203,"Super Lig",2023),
                38,
                16,
                17,
            ),
            (
                row("Turkey",203,"Super Lig",2024),
                36,
                15,
                16,
            ),
            (
                row("Turkey",203,"Super Lig",2025),
                34,
                15,
                16,
            ),
        ]

        for payload, total_games, safe_rank, direct_start in cases:
            with self.subTest(payload=payload):
                item = c.cell_contract(payload)

                self.assertEqual(item["status"], "VERIFIED")
                self.assertEqual(
                    item["source_contract"],
                    "HISTORICAL_PBK16_FORMATS",
                )
                self.assertTrue(item["title_boundary_authorized"])
                self.assertTrue(item["relegation_boundary_authorized"])
                self.assertEqual(item["total_games"], total_games)
                self.assertEqual(item["safe_rank"], safe_rank)
                self.assertEqual(
                    item["direct_relegation_start_rank"],
                    direct_start,
                )
                self.assertIsNone(
                    item["relegation_playoff_rank"]
                )

    def test_turkey_2022_temporal_exception_stays_unknown(self):
        item = c.cell_contract(
            row("Turkey",203,"Super Lig",2022)
        )

        self.assertEqual(item["status"], "UNKNOWN")
        self.assertFalse(item["title_boundary_authorized"])
        self.assertFalse(item["relegation_boundary_authorized"])



    def test_non_top5_cell_remains_unknown(self):
        item=c.cell_contract(row("Denmark",119,"Superliga",2024))
        self.assertEqual(item["status"],"UNKNOWN")
        self.assertFalse(item["title_boundary_authorized"])
        self.assertFalse(item["relegation_boundary_authorized"])

    def test_duplicate_inventory_cells_are_counted_once(self):
        rows=[
            row("England",39,"Premier League",2024),
            row("England",39,"Premier League",2024),
            row("Denmark",119,"Superliga",2024),
        ]
        report=c.build_coverage(rows)
        self.assertEqual(report["required_league_season_cells"],2)
        self.assertEqual(report["verified_league_season_cells"],1)
        self.assertEqual(report["missing_league_season_cells"],1)
        self.assertEqual(report["status"],"IN_PROGRESS")
        self.assertFalse(report["operational_betting_authority"])


if __name__=="__main__":
    unittest.main()
