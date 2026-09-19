import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_pbk16_domestic_phase_audit as s


def row(country,season,round_name,status="FT",fid="1"):
    return {
        "fixture_id":fid,
        "competition_role":"DOMESTIC_LEAGUE",
        "country":country,
        "provider_competition_id":"99",
        "competition_name":"League",
        "season":str(season),
        "round":round_name,
        "kickoff_utc":"2025-05-01T12:00:00+00:00",
        "status":status,
        "home_team_id":"10","home_team":"Home",
        "away_team_id":"20","away_team":"Away",
    }


class PBK16DomesticPhaseAuditTests(unittest.TestCase):
    def test_regular_round_is_table_phase(self):
        role,family=s.table_phase("England",2025,"Regular Season - 10")
        self.assertEqual((role,family),("TABLE_PHASE","REGULAR"))

    def test_post_table_relegation_rounds_are_not_league_table_rows(self):
        for country in ("Germany","France","Portugal","Norway","Latvia","Netherlands"):
            with self.subTest(country=country):
                role,_=s.table_phase(country,2025,"Relegation Round - 1")
                self.assertEqual(role,"POST_TABLE_PLAYOFF")

    def test_split_leagues_keep_table_bearing_phases(self):
        cases=[
            ("Austria",2024,"Championship Round - 2"),
            ("Austria",2024,"Relegation Round - 2"),
            ("Belgium",2024,"Championship Round - 2"),
            ("Belgium",2025,"Relegation Group - 2"),
            ("Denmark",2024,"Championship Round - 2"),
            ("Denmark",2024,"Relegation Round - 2"),
            ("Lithuania",2018,"Championship Round - 2"),
            ("Poland",2019,"Relegation Round - 2"),
            ("Scotland",2025,"Championship Group - 2"),
            ("Scotland",2025,"Relegation Group - 2"),
        ]
        for country,season,round_name in cases:
            with self.subTest(country=country,season=season,round=round_name):
                role,family=s.table_phase(country,season,round_name)
                self.assertEqual(role,"TABLE_PHASE")
                self.assertNotEqual(family,"REGULAR")

    def test_austria_2020_mixed_relegation_label_is_disambiguated(self):
        self.assertEqual(
            s.table_phase("Austria",2020,"Relegation Round - 10")[0],
            "TABLE_PHASE",
        )
        self.assertEqual(
            s.table_phase("Austria",2020,"Relegation Round")[0],
            "POST_TABLE_PLAYOFF",
        )

    def test_belgium_2023_2024_mixed_relegation_label_is_disambiguated(self):
        for season in (2023,2024):
            with self.subTest(season=season):
                self.assertEqual(
                    s.table_phase("Belgium",season,"Relegation Round - 6")[0],
                    "TABLE_PHASE",
                )
                self.assertEqual(
                    s.table_phase("Belgium",season,"Relegation Round")[0],
                    "POST_TABLE_PLAYOFF",
                )

    def test_scotland_2022_mixed_relegation_label_is_disambiguated(self):
        self.assertEqual(
            s.table_phase("Scotland",2022,"Relegation Round - 3")[0],
            "TABLE_PHASE",
        )
        self.assertEqual(
            s.table_phase("Scotland",2022,"Relegation Round")[0],
            "POST_TABLE_PLAYOFF",
        )

    def test_table_result_policy_fails_closed(self):
        self.assertEqual(s.result_policy("TABLE_PHASE","FT"),"PLAYED_RESULT_USABLE")
        self.assertEqual(s.result_policy("TABLE_PHASE","CANC"),"NOT_PLAYED_EXCLUDE")
        self.assertEqual(s.result_policy("TABLE_PHASE","Canc"),"NOT_PLAYED_EXCLUDE")
        self.assertEqual(
            s.result_policy("TABLE_PHASE","AWD"),
            "AWARDED_RESULT_REQUIRES_RULE_EVIDENCE",
        )
        self.assertEqual(
            s.result_policy("TABLE_PHASE","WO"),
            "AWARDED_RESULT_REQUIRES_RULE_EVIDENCE",
        )
        self.assertEqual(
            s.result_policy("TABLE_PHASE","PEN"),
            "UNSUPPORTED_TABLE_STATUS",
        )
        self.assertEqual(
            s.result_policy("POST_TABLE_PLAYOFF","PEN"),
            "NOT_FOR_LEAGUE_TABLE_RECONSTRUCTION",
        )

    def test_project_keeps_post_table_rows_but_excludes_from_future_table_reconstruction(self):
        rows=[
            row("Germany",2025,"Regular Season - 34","FT","1"),
            row("Germany",2025,"Relegation Round - 1","FT","2"),
            row("Belgium",2022,"Regular Season - 3","WO","3"),
        ]
        out=s.project(rows)
        by={x["fixture_id"]:x for x in out}
        self.assertEqual(by["1"]["included_in_future_table_reconstruction"],"true")
        self.assertEqual(by["2"]["phase_role"],"POST_TABLE_PLAYOFF")
        self.assertEqual(by["2"]["included_in_future_table_reconstruction"],"false")
        self.assertEqual(
            by["3"]["table_result_policy"],
            "AWARDED_RESULT_REQUIRES_RULE_EVIDENCE",
        )
        self.assertEqual(by["3"]["included_in_future_table_reconstruction"],"false")

    def test_nonregular_table_phase_requires_season_format_contract(self):
        out=s.project([
            row("Austria",2024,"Regular Season - 22",fid="1"),
            row("Austria",2024,"Championship Round - 1",fid="2"),
        ])
        by={x["fixture_id"]:x for x in out}
        self.assertEqual(by["1"]["season_format_contract_required"],"false")
        self.assertEqual(by["2"]["season_format_contract_required"],"true")

    def test_unknown_country_fails_closed(self):
        role,family=s.table_phase("Unknownland",2025,"Regular Season - 1")
        self.assertEqual((role,family),("UNKNOWN","UNKNOWN"))

    def test_run_small_fixture_and_state_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"archive.csv"
            state=root/"state.csv"
            out=root/"audit.csv"
            meta=root/"meta.json"
            rows=[
                row("England",2025,"Regular Season - 1","FT","1"),
                row("Germany",2025,"Relegation Round - 1","PEN","2"),
            ]
            with source.open("w",encoding="utf-8-sig",newline="") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]))
                w.writeheader();w.writerows(rows)
            state_rows=[
                {
                    "competition_role":"DOMESTIC_LEAGUE","country":"England",
                    "season":"2025","status":"CAPTURED"
                },
                {
                    "competition_role":"DOMESTIC_LEAGUE","country":"Germany",
                    "season":"2025","status":"CAPTURED"
                },
            ]
            with state.open("w",encoding="utf-8-sig",newline="") as f:
                w=csv.DictWriter(f,fieldnames=list(state_rows[0]))
                w.writeheader();w.writerows(state_rows)
            # The production run has strict exact archive counts, so a tiny fixture
            # intentionally reports ATTENTION while still materializing correct rows.
            m=s.run(source,state,out,meta)
            self.assertEqual(m["status"],"ATTENTION")
            self.assertEqual(m["domestic_rows"],2)
            self.assertEqual(m["unknown_phase_rows"],0)
            self.assertTrue(out.exists())
            self.assertTrue(meta.exists())


if __name__=="__main__":
    unittest.main()
