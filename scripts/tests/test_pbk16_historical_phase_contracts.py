import unittest

from scripts import pbk16_historical_phase_contracts as c


class PBK16HistoricalPhaseContractsTests(unittest.TestCase):
    def test_exact_season_scope_never_infers_neighboring_season(self):
        known=c.lookup("Austria","2025","CHAMPIONSHIP_SPLIT")
        future=c.lookup("Austria","2026","CHAMPIONSHIP_SPLIT")
        self.assertEqual(known["status"],c.HALVE)
        self.assertEqual(future["status"],"UNKNOWN")

    def test_carry_forward_candidates_are_not_yet_application_authorized(self):
        for key in [
            ("Denmark","2025","CHAMPIONSHIP_SPLIT"),
            ("Scotland","2025","RELEGATION_SPLIT"),
            ("Poland","2019","CHAMPIONSHIP_SPLIT"),
            ("Lithuania","2019","CHAMPIONSHIP_SPLIT"),
        ]:
            with self.subTest(key=key):
                item=c.lookup(*key)
                self.assertEqual(item["status"],c.CARRY)
                self.assertEqual(item["points_transform"],"CARRY_FORWARD_UNCHANGED")
                self.assertTrue(item["application_authorized"])
                self.assertTrue(item["group_aware_reconstruction_required"])

    def test_austria_halving_is_authorized_but_belgium_remains_blocked(self):
        austria=c.lookup("Austria","2024","RELEGATION_SPLIT")
        belgium=c.lookup("Belgium","2024","EUROPE_SPLIT")
        self.assertEqual(austria["status"],c.HALVE)
        self.assertEqual(austria["points_transform"],"FLOOR_HALF_AT_SPLIT")
        self.assertEqual(austria["half_point_rounding"],"FLOOR")
        self.assertEqual(
            austria["rounded_half_tiebreak"],
            "ROUNDED_DOWN_CLUB_FIRST",
        )
        self.assertTrue(austria["application_authorized"])
        self.assertEqual(belgium["status"],c.TRANSFORM)
        self.assertFalse(belgium["application_authorized"])
        self.assertIn("SEASON_AND_PHASE",belgium["points_transform"])

    def test_archive_shape_reconciles_to_known_1747_split_rows(self):
        rows=[]
        counts={
            ("Lithuania","2019","CHAMPIONSHIP_SPLIT"):45,
            ("Belgium","2024","CHAMPIONSHIP_SPLIT"):100,
            ("Belgium","2024","EUROPE_SPLIT"):100,
            ("Belgium","2024","RELEGATION_SPLIT"):148,
            ("Denmark","2025","CHAMPIONSHIP_SPLIT"):261,
            ("Denmark","2025","RELEGATION_SPLIT"):261,
            ("Scotland","2025","CHAMPIONSHIP_OR_SPLIT"):120,
            ("Scotland","2025","RELEGATION_SPLIT"):120,
            ("Austria","2025","CHAMPIONSHIP_SPLIT"):240,
            ("Austria","2025","RELEGATION_SPLIT"):240,
            ("Poland","2019","CHAMPIONSHIP_SPLIT"):56,
            ("Poland","2019","RELEGATION_SPLIT"):56,
        }
        # Synthetic distribution preserves the production totals by country:
        # LT 45, BE 348, DK 522, SCO 240, AUT 480, POL 112.
        for (country,season,family),n in counts.items():
            for i in range(n):
                rows.append({
                    "fixture_id":f"{country}-{family}-{i}",
                    "country":country,
                    "season":season,
                    "phase_role":"TABLE_PHASE",
                    "phase_family":family,
                    "season_format_contract_required":"true",
                })
        report=c.analyze_rows(rows)
        self.assertEqual(report["required_nonregular_table_phase_rows"],1747)
        self.assertEqual(report["contract_covered_rows"],1747)
        self.assertEqual(report["carry_forward_candidate_rows"],919)
        self.assertEqual(report["halving_authorized_rows"],480)
        self.assertEqual(report["transform_required_rows"],348)
        self.assertEqual(report["unknown_contract_rows"],0)
        self.assertEqual(report["application_authorized_rows"],1399)
        self.assertFalse(report["exact_title_relegation_motivation_allowed"])

    def test_unknown_contract_fails_closed(self):
        report=c.analyze_rows([{
            "fixture_id":"x",
            "country":"Unknown",
            "season":"2024",
            "phase_role":"TABLE_PHASE",
            "phase_family":"CHAMPIONSHIP_SPLIT",
            "season_format_contract_required":"true",
        }])
        self.assertEqual(report["status"],"ATTENTION")
        self.assertEqual(report["unknown_contract_rows"],1)
        self.assertEqual(report["application_authorized_rows"],0)


if __name__=="__main__":
    unittest.main()
