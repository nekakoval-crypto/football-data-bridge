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

    def test_turkey_2022_temporal_exception_is_verified_but_static_relegation_math_stays_closed(self):
        item = c.cell_contract(
            row("Turkey",203,"Super Lig",2022)
        )

        self.assertEqual(item["status"], "VERIFIED")
        self.assertEqual(
            item["contract_mode"],
            "TEMPORAL_RULE_REGIME",
        )
        self.assertTrue(
            item["title_boundary_authorized"]
        )
        self.assertFalse(
            item["relegation_boundary_authorized"]
        )
        self.assertEqual(
            len(item["temporal_rule_regimes"]),
            2,
        )

    def test_historical_pbk16_batch_c(self):
        cases = [
            (
                row("Norway",103,"Eliteserien",2017),
                30,
                13,
                15,
                14,
            ),
            (
                row("Norway",103,"Eliteserien",2018),
                30,
                13,
                15,
                14,
            ),
            (
                row("Norway",103,"Eliteserien",2021),
                30,
                13,
                15,
                14,
            ),
            (
                row("Norway",103,"Eliteserien",2023),
                30,
                13,
                15,
                14,
            ),
            (
                row("Portugal",94,"Primeira Liga",2021),
                34,
                15,
                17,
                16,
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



    def test_historical_pbk16_batch_d_complete_norway(self):
        for season in (2020, 2022, 2024, 2025):
            with self.subTest(season=season):
                item = c.cell_contract(
                    row("Norway",103,"Eliteserien",season)
                )

                self.assertEqual(item["status"], "VERIFIED")
                self.assertEqual(
                    item["source_contract"],
                    "HISTORICAL_PBK16_FORMATS",
                )
                self.assertTrue(item["title_boundary_authorized"])
                self.assertTrue(item["relegation_boundary_authorized"])
                self.assertEqual(item["total_games"], 30)
                self.assertEqual(item["safe_rank"], 13)
                self.assertEqual(
                    item["direct_relegation_start_rank"],
                    15,
                )
                self.assertEqual(
                    item["relegation_playoff_rank"],
                    14,
                )



    def test_super_mega_maxi_batch_e(self):
        cases = [
            # Poland
            (row("Poland",106,"Ekstraklasa",2021),34,15,16,None),
            (row("Poland",106,"Ekstraklasa",2023),34,15,16,None),
            (row("Poland",106,"Ekstraklasa",2024),34,15,16,None),
            (row("Poland",106,"Ekstraklasa",2025),34,15,16,None),

            # Portugal
            (row("Portugal",94,"Primeira Liga",2020),34,15,17,16),
            (row("Portugal",94,"Primeira Liga",2022),34,15,17,16),
            (row("Portugal",94,"Primeira Liga",2023),34,15,17,16),
            (row("Portugal",94,"Primeira Liga",2024),34,15,17,16),
            (row("Portugal",94,"Primeira Liga",2025),34,15,17,16),

            # Turkey
            (row("Turkey",203,"Super Lig",2017),34,15,16,None),
            (row("Turkey",203,"Super Lig",2018),34,15,16,None),

            # Netherlands
            (row("Netherlands",88,"Eredivisie",2020),34,15,17,16),
            (row("Netherlands",88,"Eredivisie",2021),34,15,17,16),
            (row("Netherlands",88,"Eredivisie",2022),34,15,17,16),
            (row("Netherlands",88,"Eredivisie",2023),34,15,17,16),
            (row("Netherlands",88,"Eredivisie",2024),34,15,17,16),
            (row("Netherlands",88,"Eredivisie",2025),34,15,17,16),
        ]

        self.assertEqual(len(cases), 17)

        for payload, games, safe, direct, playoff in cases:
            with self.subTest(payload=payload):
                item = c.cell_contract(payload)

                self.assertEqual(item["status"], "VERIFIED")
                self.assertEqual(
                    item["source_contract"],
                    "HISTORICAL_PBK16_FORMATS",
                )
                self.assertTrue(item["title_boundary_authorized"])
                self.assertTrue(item["relegation_boundary_authorized"])
                self.assertEqual(item["total_games"], games)
                self.assertEqual(item["safe_rank"], safe)
                self.assertEqual(
                    item["direct_relegation_start_rank"],
                    direct,
                )
                self.assertEqual(
                    item["relegation_playoff_rank"],
                    playoff,
                )


    def test_maxi_batch_temporal_exception_is_now_explicitly_verified(self):
        turkey_2022 = c.cell_contract(
            row("Turkey",203,"Super Lig",2022)
        )

        self.assertEqual(
            turkey_2022["status"],
            "VERIFIED",
        )
        self.assertEqual(
            turkey_2022["contract_mode"],
            "TEMPORAL_RULE_REGIME",
        )
        self.assertFalse(
            turkey_2022["relegation_boundary_authorized"]
        )

    def test_super_mega_maxi_batch_f(self):
        cases = [
            # country, league, name, season, games, safe, direct, playoff

            ("Austria",218,"Bundesliga",2017,36,9,None,10),

            ("Latvia",365,"Virsliga",2018,28,6,8,7),
            ("Latvia",365,"Virsliga",2019,32,8,None,9),
            ("Latvia",365,"Virsliga",2020,27,8,10,9),
            ("Latvia",365,"Virsliga",2022,36,8,10,9),
            ("Latvia",365,"Virsliga",2023,36,8,10,9),
            ("Latvia",365,"Virsliga",2024,36,8,10,9),
            ("Latvia",365,"Virsliga",2025,36,8,10,9),

            ("Lithuania",362,"A Lyga",2020,20,6,None,None),
            ("Lithuania",362,"A Lyga",2021,36,8,9,None),
            ("Lithuania",362,"A Lyga",2022,36,8,10,9),
            ("Lithuania",362,"A Lyga",2024,36,8,10,9),

            ("Portugal",94,"Primeira Liga",2017,34,16,17,None),
            ("Portugal",94,"Primeira Liga",2018,34,16,17,None),
        ]

        self.assertEqual(len(cases), 14)

        for (
            country,
            league_id,
            league_name,
            season,
            games,
            safe,
            direct,
            playoff,
        ) in cases:
            with self.subTest(
                country=country,
                season=season,
            ):
                item = c.cell_contract(
                    row(
                        country,
                        league_id,
                        league_name,
                        season,
                    )
                )

                self.assertEqual(item["status"], "VERIFIED")
                self.assertEqual(
                    item["source_contract"],
                    "HISTORICAL_PBK16_FORMATS",
                )
                self.assertTrue(
                    item["title_boundary_authorized"]
                )
                self.assertTrue(
                    item["relegation_boundary_authorized"]
                )
                self.assertEqual(
                    item["total_games"],
                    games,
                )
                self.assertEqual(
                    item["safe_rank"],
                    safe,
                )
                self.assertEqual(
                    item["direct_relegation_start_rank"],
                    direct,
                )
                self.assertEqual(
                    item["relegation_playoff_rank"],
                    playoff,
                )

    def test_batch_f_supports_three_relegation_semantics(self):
        # Playoff-only.
        austria = c.cell_contract(
            row("Austria",218,"Bundesliga",2017)
        )
        self.assertIsNone(
            austria["direct_relegation_start_rank"]
        )
        self.assertEqual(
            austria["relegation_playoff_rank"],
            10,
        )
        self.assertEqual(austria["safe_rank"], 9)

        # Another playoff-only historical contract.
        latvia = c.cell_contract(
            row("Latvia",365,"Virsliga",2019)
        )
        self.assertIsNone(
            latvia["direct_relegation_start_rank"]
        )
        self.assertEqual(
            latvia["relegation_playoff_rank"],
            9,
        )

        # Verified no-relegation season.
        lithuania = c.cell_contract(
            row("Lithuania",362,"A Lyga",2020)
        )
        self.assertIsNone(
            lithuania["direct_relegation_start_rank"]
        )
        self.assertIsNone(
            lithuania["relegation_playoff_rank"]
        )
        self.assertEqual(lithuania["safe_rank"], 6)

    def test_batch_f_temporal_and_complex_exceptions_stay_unknown(self):
        exceptions = [
        ]

        for payload in exceptions:
            with self.subTest(payload=payload):
                item = c.cell_contract(payload)
                self.assertEqual(item["status"], "UNKNOWN")
                self.assertFalse(
                    item["title_boundary_authorized"]
                )
                self.assertFalse(
                    item["relegation_boundary_authorized"]
                )



    def test_super_mega_maxi_batch_g_phase_aware(self):
        cases = []

        for season in range(2018, 2026):
            cases.append(
                (
                    row("Austria",218,"Bundesliga",season),
                    32,
                    11,
                    12,
                    None,
                    "SPLIT_TOP6_BOTTOM6",
                    22,
                    10,
                    "HALVE_FLOOR",
                )
            )

        for season in range(2020, 2026):
            cases.append(
                (
                    row("Denmark",119,"Superliga",season),
                    32,
                    10,
                    11,
                    None,
                    "SPLIT_TOP6_BOTTOM6",
                    22,
                    10,
                    "NONE",
                )
            )

        for season in range(2020, 2026):
            cases.append(
                (
                    row("Scotland",179,"Premiership",season),
                    38,
                    10,
                    12,
                    11,
                    "SPLIT_TOP6_BOTTOM6",
                    33,
                    5,
                    "NONE",
                )
            )

        self.assertEqual(len(cases), 20)

        for (
            payload,
            games,
            safe,
            direct,
            playoff,
            format_type,
            regular_games,
            post_split,
            transform,
        ) in cases:
            with self.subTest(payload=payload):
                item = c.cell_contract(payload)

                self.assertEqual(
                    item["status"],
                    "VERIFIED",
                )
                self.assertEqual(
                    item["source_contract"],
                    "HISTORICAL_PBK16_FORMATS",
                )
                self.assertTrue(
                    item["title_boundary_authorized"]
                )
                self.assertTrue(
                    item["relegation_boundary_authorized"]
                )

                self.assertEqual(
                    item["total_games"],
                    games,
                )
                self.assertEqual(
                    item["safe_rank"],
                    safe,
                )
                self.assertEqual(
                    item["direct_relegation_start_rank"],
                    direct,
                )
                self.assertEqual(
                    item["relegation_playoff_rank"],
                    playoff,
                )

                self.assertTrue(
                    item["phase_aware"]
                )
                self.assertEqual(
                    item["format_type"],
                    format_type,
                )
                self.assertEqual(
                    item["regular_phase_games"],
                    regular_games,
                )
                self.assertEqual(
                    item["post_split_games"],
                    post_split,
                )
                self.assertEqual(
                    item["points_transform"],
                    transform,
                )


    def test_batch_g_phase_semantics_are_not_flattened(self):
        austria = c.cell_contract(
            row("Austria",218,"Bundesliga",2024)
        )
        denmark = c.cell_contract(
            row("Denmark",119,"Superliga",2024)
        )
        scotland = c.cell_contract(
            row("Scotland",179,"Premiership",2024)
        )

        self.assertEqual(
            austria["points_transform"],
            "HALVE_FLOOR",
        )
        self.assertEqual(
            austria["regular_phase_games"],
            22,
        )
        self.assertEqual(
            austria["post_split_games"],
            10,
        )

        self.assertEqual(
            denmark["points_transform"],
            "NONE",
        )
        self.assertEqual(
            denmark["regular_phase_games"],
            22,
        )

        self.assertEqual(
            scotland["regular_phase_games"],
            33,
        )
        self.assertEqual(
            scotland["post_split_games"],
            5,
        )
        self.assertEqual(
            scotland["relegation_playoff_rank"],
            11,
        )


    def test_batch_g_known_exceptions_remain_unknown(self):
        exceptions = [
        ]

        for payload in exceptions:
            with self.subTest(payload=payload):
                item = c.cell_contract(payload)
                self.assertEqual(
                    item["status"],
                    "UNKNOWN",
                )



    def test_batch_h_playoff_range_semantics(self):
        nl_cases = [
            row("Netherlands",88,"Eredivisie",2017),
            row("Netherlands",88,"Eredivisie",2018),
        ]

        for payload in nl_cases:
            with self.subTest(payload=payload):
                item = c.cell_contract(payload)
                self.assertEqual(item["status"], "VERIFIED")
                self.assertEqual(item["safe_rank"], 15)
                self.assertEqual(
                    item["direct_relegation_start_rank"],
                    18,
                )
                self.assertIsNone(
                    item["relegation_playoff_rank"]
                )
                self.assertEqual(
                    item["relegation_playoff_start_rank"],
                    16,
                )
                self.assertEqual(
                    item["relegation_playoff_end_rank"],
                    17,
                )

        latvia = c.cell_contract(
            row("Latvia",365,"Virsliga",2021)
        )
        self.assertEqual(latvia["status"], "VERIFIED")
        self.assertEqual(latvia["total_games"], 32)
        self.assertEqual(latvia["safe_rank"], 8)
        self.assertIsNone(
            latvia["direct_relegation_start_rank"]
        )
        self.assertEqual(
            latvia["relegation_playoff_rank"],
            9,
        )

        scotland = c.cell_contract(
            row("Scotland",179,"Premiership",2018)
        )
        self.assertEqual(scotland["status"], "VERIFIED")
        self.assertTrue(scotland["phase_aware"])
        self.assertEqual(
            scotland["regular_phase_games"],
            33,
        )
        self.assertEqual(
            scotland["post_split_games"],
            5,
        )
        self.assertEqual(
            scotland["direct_relegation_start_rank"],
            12,
        )
        self.assertEqual(
            scotland["relegation_playoff_rank"],
            11,
        )



    def test_batch_i_objective_specific_horizons(self):
        for season in (2017, 2018, 2019):
            with self.subTest(season=season):
                item = c.cell_contract(
                    row("Lithuania",362,"A Lyga",season)
                )

                self.assertEqual(item["status"], "VERIFIED")
                self.assertTrue(item["phase_aware"])

                self.assertEqual(
                    item["format_type"],
                    "ASYMMETRIC_TOP6_FINAL_ROUND",
                )
                self.assertEqual(
                    item["regular_phase_games"],
                    28,
                )
                self.assertEqual(
                    item["post_split_games"],
                    5,
                )

                self.assertEqual(
                    item["title_total_games"],
                    33,
                )
                self.assertEqual(
                    item["relegation_total_games"],
                    28,
                )

                self.assertEqual(item["safe_rank"], 6)
                self.assertEqual(
                    item["relegation_playoff_rank"],
                    7,
                )
                self.assertEqual(
                    item["direct_relegation_start_rank"],
                    8,
                )

        for season in (2023, 2025):
            item = c.cell_contract(
                row("Lithuania",362,"A Lyga",season)
            )
            self.assertEqual(item["status"], "VERIFIED")
            self.assertEqual(item["total_games"], 36)
            self.assertEqual(item["title_total_games"], 36)
            self.assertEqual(
                item["relegation_total_games"],
                36,
            )
            self.assertEqual(
                item["direct_relegation_start_rank"],
                10,
            )
            self.assertEqual(
                item["relegation_playoff_rank"],
                9,
            )

        scotland = c.cell_contract(
            row("Scotland",179,"Premiership",2017)
        )
        self.assertEqual(scotland["status"], "VERIFIED")
        self.assertTrue(scotland["phase_aware"])
        self.assertEqual(
            scotland["regular_phase_games"],
            33,
        )
        self.assertEqual(
            scotland["post_split_games"],
            5,
        )
        self.assertEqual(
            scotland["direct_relegation_start_rank"],
            12,
        )
        self.assertEqual(
            scotland["relegation_playoff_rank"],
            11,
        )


    def test_batch_i_does_not_flatten_lithuania_old_format(self):
        item = c.cell_contract(
            row("Lithuania",362,"A Lyga",2018)
        )

        self.assertNotEqual(
            item["title_total_games"],
            item["relegation_total_games"],
        )

        self.assertEqual(
            item["title_total_games"],
            33,
        )
        self.assertEqual(
            item["relegation_total_games"],
            28,
        )



    def test_batch_j_verified_exception_semantics(self):
        # Final season resolutions must never rewrite what was
        # knowable before historical fixtures.

        netherlands = c.cell_contract(
            row("Netherlands",88,"Eredivisie",2019)
        )

        self.assertEqual(netherlands["status"], "VERIFIED")
        self.assertEqual(
            netherlands["contract_mode"],
            "STATIC_PREMATCH_WITH_LATER_FINAL_RESOLUTION",
        )
        self.assertTrue(
            netherlands["title_boundary_authorized"]
        )
        self.assertTrue(
            netherlands["relegation_boundary_authorized"]
        )
        self.assertEqual(
            netherlands["direct_relegation_start_rank"],
            17,
        )
        self.assertEqual(
            netherlands["relegation_playoff_rank"],
            16,
        )
        self.assertEqual(
            netherlands["final_resolution"]["title_status"],
            "NO_CHAMPION",
        )
        self.assertEqual(
            netherlands["final_resolution"]["relegation_status"],
            "NO_RELEGATION",
        )

        turkey = c.cell_contract(
            row("Turkey",203,"Super Lig",2019)
        )

        self.assertEqual(turkey["status"], "VERIFIED")
        self.assertTrue(
            turkey["relegation_boundary_authorized"]
        )
        self.assertEqual(
            turkey["direct_relegation_start_rank"],
            16,
        )
        self.assertEqual(
            turkey["final_resolution"]["relegation_status"],
            "NO_RELEGATION",
        )

    def test_batch_k_scotland_and_poland_2019(self):
        scotland = c.cell_contract(
            row("Scotland",179,"Premiership",2019)
        )

        self.assertEqual(scotland["status"], "VERIFIED")
        self.assertEqual(
            scotland["contract_mode"],
            "STATIC_PREMATCH_WITH_LATER_FINAL_RESOLUTION",
        )
        self.assertEqual(
            scotland["format_type"],
            "SPLIT_TOP6_BOTTOM6",
        )
        self.assertEqual(
            scotland["points_transform"],
            "NONE",
        )
        self.assertEqual(
            scotland["direct_relegation_start_rank"],
            12,
        )
        self.assertEqual(
            scotland["relegation_playoff_rank"],
            11,
        )
        self.assertTrue(
            scotland["title_boundary_authorized"]
        )
        self.assertTrue(
            scotland["relegation_boundary_authorized"]
        )
        self.assertEqual(
            scotland["final_resolution"]["ranking_method"],
            "POINTS_PER_GAME",
        )

        poland = c.cell_contract(
            row("Poland",106,"Ekstraklasa",2019)
        )

        self.assertEqual(poland["status"], "VERIFIED")
        self.assertEqual(
            poland["format_type"],
            "SPLIT_TOP8_BOTTOM8",
        )
        self.assertTrue(poland["phase_aware"])
        self.assertEqual(poland["regular_phase_games"], 30)
        self.assertEqual(poland["post_split_games"], 7)
        self.assertEqual(poland["points_transform"], "NONE")
        self.assertEqual(poland["total_games"], 37)
        self.assertEqual(
            poland["direct_relegation_start_rank"],
            14,
        )
        self.assertEqual(poland["safe_rank"], 13)

    def test_non_top5_cell_remains_unknown(self):
        # A season outside required reconstructed coverage remains
        # fail-closed even after Mega L.
        item = c.cell_contract(
            row("Belgium",144,"Jupiler Pro League",2016)
        )
        self.assertEqual(item["status"], "UNKNOWN")
        self.assertFalse(item["title_boundary_authorized"])
        self.assertFalse(
            item["relegation_boundary_authorized"]
        )

    def test_mega_l_final_sixteen_contracts(self):
        cases = [
            *[
                row(
                    "Belgium",
                    144,
                    "Jupiler Pro League",
                    season,
                )
                for season in range(2017, 2026)
            ],
            *[
                row(
                    "Denmark",
                    119,
                    "Superliga",
                    season,
                )
                for season in range(2017, 2020)
            ],
            row("Latvia",365,"Virsliga",2017),
            row("Poland",106,"Ekstraklasa",2018),
            row("Portugal",94,"Primeira Liga",2019),
            row("Turkey",203,"Super Lig",2022),
        ]

        self.assertEqual(len(cases), 16)

        for payload in cases:
            with self.subTest(payload=payload):
                item = c.cell_contract(payload)
                self.assertEqual(item["status"], "VERIFIED")
                self.assertEqual(
                    item["source_contract"],
                    "HISTORICAL_PBK16_FORMATS",
                )
                self.assertTrue(item["source"])

        # Complex Belgian math is verified evidence but remains
        # unauthorized for one static formula.
        belgium = c.cell_contract(
            row("Belgium",144,"Jupiler Pro League",2024)
        )
        self.assertEqual(
            belgium["contract_mode"],
            "MULTI_STAGE_RELEGATION",
        )
        self.assertFalse(
            belgium["title_boundary_authorized"]
        )
        self.assertFalse(
            belgium["relegation_boundary_authorized"]
        )
        self.assertEqual(
            belgium["title_points_transform"],
            "HALVE_WITH_ODD_ROUNDING",
        )
        self.assertEqual(
            belgium["relegation_points_transform"],
            "NONE",
        )

        denmark = c.cell_contract(
            row("Denmark",119,"Superliga",2018)
        )
        self.assertEqual(
            denmark["contract_mode"],
            "MULTI_STAGE_RELEGATION",
        )
        self.assertFalse(
            denmark["relegation_boundary_authorized"]
        )
        self.assertTrue(
            denmark["relegation_horizon_variable"]
        )

        latvia = c.cell_contract(
            row("Latvia",365,"Virsliga",2017)
        )
        self.assertEqual(
            latvia["contract_mode"],
            "TEMPORAL_RULE_REGIME",
        )
        self.assertFalse(
            latvia["relegation_boundary_authorized"]
        )
        self.assertEqual(
            len(latvia["temporal_rule_regimes"]),
            2,
        )

        poland = c.cell_contract(
            row("Poland",106,"Ekstraklasa",2018)
        )
        self.assertTrue(
            poland["title_boundary_authorized"]
        )
        self.assertTrue(
            poland["relegation_boundary_authorized"]
        )
        self.assertEqual(poland["total_games"], 37)
        self.assertEqual(
            poland["direct_relegation_start_rank"],
            15,
        )

        portugal = c.cell_contract(
            row("Portugal",94,"Primeira Liga",2019)
        )
        self.assertEqual(portugal["total_games"], 34)
        self.assertEqual(
            portugal["direct_relegation_start_rank"],
            17,
        )
        self.assertTrue(
            portugal["relegation_boundary_authorized"]
        )

        turkey = c.cell_contract(
            row("Turkey",203,"Super Lig",2022)
        )
        self.assertEqual(
            turkey["contract_mode"],
            "TEMPORAL_RULE_REGIME",
        )
        self.assertTrue(
            turkey["title_boundary_authorized"]
        )
        self.assertFalse(
            turkey["relegation_boundary_authorized"]
        )
        self.assertEqual(
            len(turkey["temporal_rule_regimes"]),
            2,
        )


    def test_mega_l_verified_does_not_mean_betting_authority(self):
        report = c.build_coverage()

        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(
            report["required_league_season_cells"],
            143,
        )
        self.assertEqual(
            report["verified_league_season_cells"],
            143,
        )
        self.assertEqual(
            report["missing_league_season_cells"],
            0,
        )

        self.assertTrue(
            report[
                "all_exact_title_relegation_contracts_verified"
            ]
        )

        self.assertFalse(
            report["operational_betting_authority"]
        )
        self.assertFalse(report["probability_mutation"])
        self.assertFalse(report["eligibility_mutation"])
        self.assertFalse(report["stake_changes"])



    def test_duplicate_inventory_cells_are_counted_once(self):
        rows=[
            row("England",39,"Premier League",2024),
            row("England",39,"Premier League",2024),
            row("Belgium",144,"Jupiler Pro League",2016),
        ]
        report=c.build_coverage(rows)
        self.assertEqual(report["required_league_season_cells"],2)
        self.assertEqual(report["verified_league_season_cells"],1)
        self.assertEqual(report["missing_league_season_cells"],1)
        self.assertEqual(report["status"],"IN_PROGRESS")
        self.assertFalse(report["operational_betting_authority"])


if __name__=="__main__":
    unittest.main()
