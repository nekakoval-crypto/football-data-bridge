import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import motivation_rivalry


class MotivationRivalryTests(unittest.TestCase):
    def test_madrid_derby_is_verified_in_both_directions(self):
        first = motivation_rivalry.lookup_rivalry(
            "Atletico Madrid",
            "Real Madrid",
        )
        second = motivation_rivalry.lookup_rivalry(
            "Real Madrid",
            "Atlético de Madrid",
        )
        for payload in (first, second):
            self.assertEqual(payload["status"], "VERIFIED")
            self.assertTrue(payload["derby"])
            self.assertTrue(payload["principled_rivalry"])
            self.assertTrue(payload["independent_of_table_pressure"])
            self.assertEqual(payload["rivalry_id"], "ESP_MADRID_DERBY_REAL_ATLETICO")

    def test_representative_pbk16_rivalries_are_exact_match_only(self):
        cases = [
            ("Arsenal", "Tottenham Hotspur", "ENG_NORTH_LONDON", True),
            ("AC Milan", "Inter Milan", "ITA_DERBY_DELLA_MADONNINA", True),
            ("Bayern Munich", "Borussia Dortmund", "GER_KLASSIKER_BAYERN_DORTMUND", False),
            ("Paris Saint-Germain", "Olympique de Marseille", "FRA_LE_CLASSIQUE", False),
            ("Ajax Amsterdam", "Feyenoord Rotterdam", "NED_DE_KLASSIEKER", False),
            ("Benfica", "Sporting CP", "POR_LISBON_DERBY", True),
            ("Fenerbahçe", "Galatasaray", "TUR_INTERCONTINENTAL_DERBY", True),
            ("Celtic", "Rangers", "SCO_OLD_FIRM", True),
        ]
        for home, away, rivalry_id, is_derby in cases:
            with self.subTest(rivalry_id=rivalry_id):
                payload = motivation_rivalry.lookup_rivalry(home, away)
                self.assertEqual(payload["status"], "VERIFIED")
                self.assertEqual(payload["rivalry_id"], rivalry_id)
                self.assertEqual(payload["derby"], is_derby)
                self.assertTrue(payload["principled_rivalry"])

    def test_catalog_represents_all_pbk16_leagues_but_stays_partial(self):
        registry = motivation_rivalry.load_registry()
        scopes = {
            str(row.get("competition_scope") or "").upper()
            for row in registry["rivalries"]
        }
        expected = {
            "ENGLAND", "SPAIN", "ITALY", "GERMANY", "FRANCE",
            "AUSTRIA", "BELGIUM", "DENMARK", "LITHUANIA", "LATVIA",
            "NETHERLANDS", "NORWAY", "POLAND", "PORTUGAL", "TURKEY",
            "SCOTLAND",
        }
        self.assertEqual(scopes, expected)
        self.assertEqual(
            registry["coverage"]["pbk16_leagues_represented"],
            16,
        )
        self.assertEqual(registry["coverage"]["catalog_completeness"], "PARTIAL")
        self.assertEqual(registry["status"], "PARTIAL_VERIFIED_CATALOG")

    def test_historical_lithuania_trakai_alias_resolves_vilnius_derby(self):
        payload = motivation_rivalry.lookup_rivalry(
            "FK Zalgiris Vilnius",
            "FK Trakai",
        )
        self.assertEqual(payload["status"], "VERIFIED")
        self.assertEqual(payload["rivalry_id"], "LTU_VILNIUS_DERBY")
        self.assertTrue(payload["derby"])


    def test_historical_latvia_rigas_fs_alias_resolves_riga_derby(self):
        payload = motivation_rivalry.lookup_rivalry(
            "Riga",
            "R\u012bgas FS",
        )
        self.assertEqual(payload["status"], "VERIFIED")
        self.assertEqual(payload["rivalry_id"], "LVA_RIGA_DERBY")
        self.assertTrue(payload["derby"])



    def test_unknown_pair_stays_unknown(self):
        payload = motivation_rivalry.lookup_rivalry("Alpha", "Beta")
        self.assertEqual(payload["status"], "UNKNOWN")
        self.assertFalse(payload["derby"])
        self.assertIsNone(payload["rivalry_id"])

    def test_no_fuzzy_match(self):
        payload = motivation_rivalry.lookup_rivalry(
            "Real Madrd",
            "Atletico Madrid",
        )
        self.assertEqual(payload["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
