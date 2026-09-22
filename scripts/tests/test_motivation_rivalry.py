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

    def test_historical_lithuania_vilnius_derby_is_time_bounded(self):
        before_move = motivation_rivalry.lookup_rivalry(
            "FK Zalgiris Vilnius",
            "FK Trakai",
            season="2018",
        )
        after_move_provider_alias = motivation_rivalry.lookup_rivalry(
            "FK Zalgiris Vilnius",
            "FK Trakai",
            season="2019",
        )
        current_identity = motivation_rivalry.lookup_rivalry(
            "FK Zalgiris Vilnius",
            "FK Riteriai",
            season="2019",
        )
        missing_season = motivation_rivalry.lookup_rivalry(
            "FK Zalgiris Vilnius",
            "FK Trakai",
        )

        self.assertEqual(before_move["status"], "UNKNOWN")
        self.assertEqual(missing_season["status"], "UNKNOWN")

        for payload in (
            after_move_provider_alias,
            current_identity,
        ):
            self.assertEqual(payload["status"], "VERIFIED")
            self.assertEqual(
                payload["rivalry_id"],
                "LTU_VILNIUS_DERBY",
            )
            self.assertTrue(payload["derby"])
            self.assertEqual(
                payload["rivalry_classes"],
                ["CITY_DERBY"],
            )
            self.assertEqual(
                payload["valid_from_season"],
                2019,
            )


    def test_historical_latvia_rigas_fs_alias_resolves_riga_derby(self):
        payload = motivation_rivalry.lookup_rivalry(
            "Riga",
            "R\u012bgas FS",
        )
        self.assertEqual(payload["status"], "VERIFIED")
        self.assertEqual(payload["rivalry_id"], "LVA_RIGA_DERBY")
        self.assertTrue(payload["derby"])



    def test_tyne_wear_has_structured_v2_classes(self):
        payload = motivation_rivalry.lookup_rivalry(
            "Newcastle United",
            "Sunderland",
            season="2025",
        )
        self.assertEqual(payload["status"], "VERIFIED")
        self.assertEqual(payload["rivalry_id"], "ENG_TYNE_WEAR")
        self.assertTrue(payload["derby"])
        self.assertTrue(payload["derby_label"])
        self.assertEqual(
            payload["rivalry_classes"],
            ["LOCAL_DERBY", "HISTORIC_RIVALRY"],
        )


    def test_palace_brighton_keeps_legacy_rivalry_but_derby_label(self):
        payload = motivation_rivalry.lookup_rivalry(
            "Crystal Palace",
            "Brighton",
            season="2025",
        )
        self.assertEqual(payload["status"], "VERIFIED")
        self.assertEqual(payload["rivalry_id"], "ENG_PALACE_BRIGHTON")
        self.assertEqual(payload["rivalry_type"], "RIVALRY")
        self.assertTrue(payload["derby"])
        self.assertTrue(payload["derby_label"])
        self.assertEqual(
            payload["rivalry_classes"],
            ["HISTORIC_RIVALRY"],
        )


    def test_migrated_contract_remains_backward_compatible(self):
        payload = motivation_rivalry.lookup_rivalry(
            "Arsenal",
            "Tottenham",
            season="2025",
        )
        self.assertEqual(payload["status"], "VERIFIED")
        self.assertTrue(payload["derby"])
        self.assertTrue(payload["derby_label"])
        self.assertEqual(
            payload["rivalry_classes"],
            ["LOCAL_DERBY", "HISTORIC_RIVALRY"],
        )


    def test_time_bounded_contract_is_fail_closed(self):
        registry = {
            "version": "TEST_V2",
            "status": "TEST",
            "rivalries": [
                {
                    "id": "TEST_BOUND",
                    "rivalry_name": "Bounded rivalry",
                    "rivalry_type": "RIVALRY",
                    "rivalry_classes": ["HISTORIC_RIVALRY"],
                    "derby_label": False,
                    "valid_from_season": 2020,
                    "valid_to_season": 2022,
                    "principled_rivalry": True,
                    "team_a_aliases": ["Alpha"],
                    "team_b_aliases": ["Beta"],
                }
            ],
        }

        inside = motivation_rivalry.lookup_rivalry(
            "Alpha",
            "Beta",
            season="2021",
            registry=registry,
        )
        before = motivation_rivalry.lookup_rivalry(
            "Alpha",
            "Beta",
            season="2019",
            registry=registry,
        )
        after = motivation_rivalry.lookup_rivalry(
            "Alpha",
            "Beta",
            season="2023",
            registry=registry,
        )
        unknown_season = motivation_rivalry.lookup_rivalry(
            "Alpha",
            "Beta",
            registry=registry,
        )

        self.assertEqual(inside["status"], "VERIFIED")
        self.assertEqual(before["status"], "UNKNOWN")
        self.assertEqual(after["status"], "UNKNOWN")
        self.assertEqual(unknown_season["status"], "UNKNOWN")



    def test_all_registry_contracts_have_v2_semantics(self):
        registry = motivation_rivalry.load_registry()

        allowed = {
            "LOCAL_DERBY",
            "CITY_DERBY",
            "REGIONAL_DERBY",
            "NATIONAL_RIVALRY",
            "HISTORIC_RIVALRY",
        }

        for row in registry["rivalries"]:
            with self.subTest(rivalry_id=row["id"]):
                self.assertIn("rivalry_classes", row)
                self.assertTrue(row["rivalry_classes"])
                self.assertTrue(
                    set(row["rivalry_classes"]).issubset(allowed)
                )
                self.assertIn("derby_label", row)
                self.assertIn("valid_from_season", row)
                self.assertIn("valid_to_season", row)



    def test_verified_england_rivalry_expansion(self):
        cases = [
            (
                "Liverpool",
                "Everton",
                "ENG_MERSEYSIDE_DERBY",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Manchester United",
                "Manchester City",
                "ENG_MANCHESTER_DERBY",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Liverpool",
                "Manchester United",
                "ENG_LIVERPOOL_MAN_UTD",
                False,
                ["NATIONAL_RIVALRY", "HISTORIC_RIVALRY"],
            ),
        ]

        for home, away, rid, derby, classes in cases:
            with self.subTest(rivalry_id=rid):
                payload = motivation_rivalry.lookup_rivalry(
                    home,
                    away,
                    season="2025",
                )

                self.assertEqual(payload["status"], "VERIFIED")
                self.assertEqual(payload["rivalry_id"], rid)
                self.assertEqual(payload["derby"], derby)
                self.assertEqual(
                    payload["rivalry_classes"],
                    classes,
                )



    def test_verified_spain_rivalry_expansion(self):
        cases = [
            (
                "Barcelona",
                "Real Madrid",
                "ESP_EL_CLASICO",
                False,
                ["NATIONAL_RIVALRY", "HISTORIC_RIVALRY"],
            ),
            (
                "Sevilla",
                "Real Betis",
                "ESP_SEVILLE_DERBY",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Athletic Club",
                "Real Sociedad",
                "ESP_BASQUE_DERBY",
                True,
                ["REGIONAL_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Barcelona",
                "Espanyol",
                "ESP_BARCELONA_DERBY",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
            ),
        ]

        for home, away, rid, derby, classes in cases:
            with self.subTest(rivalry_id=rid):
                payload = motivation_rivalry.lookup_rivalry(
                    home,
                    away,
                    season="2025",
                )

                self.assertEqual(payload["status"], "VERIFIED")
                self.assertEqual(payload["rivalry_id"], rid)
                self.assertEqual(payload["derby"], derby)
                self.assertEqual(
                    payload["rivalry_classes"],
                    classes,
                )



    def test_verified_italy_rivalry_expansion(self):
        cases = [
            ("Juventus", "Inter", "ITA_DERBY_DITALIA", False,
             ["NATIONAL_RIVALRY", "HISTORIC_RIVALRY"]),
            ("AS Roma", "Lazio", "ITA_ROME_DERBY", True,
             ["CITY_DERBY", "HISTORIC_RIVALRY"]),
            ("Juventus", "Torino", "ITA_TURIN_DERBY", True,
             ["CITY_DERBY", "HISTORIC_RIVALRY"]),
            ("Genoa", "Sampdoria", "ITA_GENOA_DERBY", True,
             ["CITY_DERBY", "HISTORIC_RIVALRY"]),
        ]

        for home, away, rid, derby, classes in cases:
            with self.subTest(rivalry_id=rid):
                payload = motivation_rivalry.lookup_rivalry(
                    home,
                    away,
                    season="2025",
                )

                self.assertEqual(payload["status"], "VERIFIED")
                self.assertEqual(payload["rivalry_id"], rid)
                self.assertEqual(payload["derby"], derby)
                self.assertEqual(payload["rivalry_classes"], classes)



    def test_verified_clean_multi_league_batch_1(self):
        cases = [
            (
                "Hamburger SV",
                "Werder Bremen",
                "GER_NORDDERBY",
                True,
                ["REGIONAL_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Hertha Berlin",
                "Union Berlin",
                "GER_BERLIN_DERBY",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Grazer AK",
                "Sturm Graz",
                "AUT_GRAZ_DERBY",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Cercle Brugge",
                "Club Brugge KV",
                "BEL_BRUGES_DERBY",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Antwerp",
                "Beerschot VA",
                "BEL_ANTWERP_DERBY",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Lens",
                "Lille",
                "FRA_DERBY_DU_NORD",
                True,
                ["REGIONAL_DERBY", "HISTORIC_RIVALRY"],
            ),
        ]

        for home, away, rid, derby, classes in cases:
            with self.subTest(rivalry_id=rid):
                payload = motivation_rivalry.lookup_rivalry(
                    home,
                    away,
                    season="2025",
                )

                self.assertEqual(payload["status"], "VERIFIED")
                self.assertEqual(payload["rivalry_id"], rid)
                self.assertEqual(payload["derby"], derby)
                self.assertEqual(
                    payload["rivalry_classes"],
                    classes,
                )



    def test_verified_clean_multi_league_batch_2(self):
        cases = [
            ("Ajax", "PSV", "NED_AJAX_PSV", False,
             ["NATIONAL_RIVALRY", "HISTORIC_RIVALRY"]),
            ("Sparta Rotterdam", "Feyenoord", "NED_ROTTERDAM_DERBY", True,
             ["CITY_DERBY", "HISTORIC_RIVALRY"]),
            ("NEC Nijmegen", "Vitesse", "NED_GELDERLAND_DERBY", True,
             ["REGIONAL_DERBY", "HISTORIC_RIVALRY"]),
            ("Valerenga", "Lillestrom", "NOR_VALERENGA_LILLESTROM", True,
             ["LOCAL_DERBY", "HISTORIC_RIVALRY"]),
            ("Brann", "Viking", "NOR_BRANN_VIKING", True,
             ["REGIONAL_DERBY", "HISTORIC_RIVALRY"]),
            ("Benfica", "FC Porto", "POR_O_CLASSICO", False,
             ["NATIONAL_RIVALRY", "HISTORIC_RIVALRY"]),
            ("FC Porto", "Boavista", "POR_PORTO_DERBY", True,
             ["CITY_DERBY", "HISTORIC_RIVALRY"]),
            ("Heart Of Midlothian", "Hibernian", "SCO_EDINBURGH_DERBY", True,
             ["CITY_DERBY", "HISTORIC_RIVALRY"]),
        ]

        for home, away, rid, derby, classes in cases:
            with self.subTest(rivalry_id=rid):
                payload = motivation_rivalry.lookup_rivalry(
                    home,
                    away,
                    season="2025",
                )

                self.assertEqual(payload["status"], "VERIFIED")
                self.assertEqual(payload["rivalry_id"], rid)
                self.assertEqual(payload["derby"], derby)
                self.assertEqual(
                    payload["rivalry_classes"],
                    classes,
                )



    def test_verified_dirty_positive_batch(self):
        cases = [
            (
                "FC Midtjylland",
                "Viborg",
                "DEN_MIDTJYLLAND_VIBORG",
                True,
                ["REGIONAL_DERBY"],
            ),
            (
                "Cracovia",
                "Wisla Krakow",
                "POL_HOLY_WAR",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
            ),
            (
                "Legia Warszawa",
                "Wisla Krakow",
                "POL_LEGIA_WISLA",
                False,
                ["NATIONAL_RIVALRY", "HISTORIC_RIVALRY"],
            ),
            (
                "Liepaja",
                "Ventspils",
                "LVA_KURZEME_DERBY",
                True,
                ["REGIONAL_DERBY", "HISTORIC_RIVALRY"],
            ),
        ]

        for home, away, rid, derby, classes in cases:
            with self.subTest(rivalry_id=rid):
                payload = motivation_rivalry.lookup_rivalry(
                    home,
                    away,
                    season="2020",
                )

                self.assertEqual(payload["status"], "VERIFIED")
                self.assertEqual(payload["rivalry_id"], rid)
                self.assertEqual(payload["derby"], derby)
                self.assertEqual(
                    payload["rivalry_classes"],
                    classes,
                )



    def test_zero_match_alias_recovery_batch(self):
        cases = [
            (
                "Borussia Dortmund",
                "FC Schalke 04",
                "GER_REVIERDERBY",
                True,
            ),
            (
                "1. FC K\u00f6ln",
                "Borussia Monchengladbach",
                "GER_RHINE_DERBY_KOLN_GLADBACH",
                True,
            ),
            (
                "Lyon",
                "Saint Etienne",
                "FRA_RHONE_DERBY",
                True,
            ),
            (
                "Lech Poznan",
                "Warta Pozna\u0144",
                "POL_POZNAN_DERBY",
                True,
            ),
            (
                "Be\u015fikta\u015f",
                "Fenerbah\u00e7e",
                "TUR_BESIKTAS_FENER",
                True,
            ),
            (
                "Be\u015fikta\u015f",
                "Galatasaray",
                "TUR_BESIKTAS_GALA",
                True,
            ),
            (
                "Fenerbah\u00e7e",
                "Trabzonspor",
                "TUR_FENER_TRABZON",
                False,
            ),
            (
                "Dundee",
                "Dundee Utd",
                "SCO_DUNDEE_DERBY",
                True,
            ),
        ]

        for home, away, rid, derby in cases:
            with self.subTest(rivalry_id=rid):
                payload = motivation_rivalry.lookup_rivalry(
                    home,
                    away,
                    season="2022",
                )

                self.assertEqual(payload["status"], "VERIFIED")
                self.assertEqual(payload["rivalry_id"], rid)
                self.assertEqual(payload["derby"], derby)


    def test_final_rivalry_tail(self):
        cases = [
            (
                "Kauno \u017dalgiris",
                "Hegelmann Litauen",
                "LTU_KAUNAS_DERBY",
                True,
                ["CITY_DERBY"],
                "2022",
            ),
            (
                "\u0141KS \u0141\u00f3d\u017a",
                "Widzew \u0141\u00f3d\u017a",
                "POL_LODZ_DERBY",
                True,
                ["CITY_DERBY", "HISTORIC_RIVALRY"],
                "2024",
            ),
            (
                "SC Braga",
                "Vit\u00f3ria SC",
                "POR_MINHO_DERBY",
                True,
                ["REGIONAL_DERBY", "HISTORIC_RIVALRY"],
                "2025",
            ),
        ]

        for home, away, rid, derby, classes, season in cases:
            with self.subTest(rivalry_id=rid):
                payload = motivation_rivalry.lookup_rivalry(
                    home,
                    away,
                    season=season,
                )

                self.assertEqual(
                    payload["status"],
                    "VERIFIED",
                )
                self.assertEqual(
                    payload["rivalry_id"],
                    rid,
                )
                self.assertEqual(
                    payload["derby"],
                    derby,
                )
                self.assertEqual(
                    payload["rivalry_classes"],
                    classes,
                )



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
