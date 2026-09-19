import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_international_duty_provider_catalog as c


def payload():
    return {
        "response":[
            {
                "league":{"id":1,"name":"World Cup - Qualification Europe","type":"Cup"},
                "country":{"name":"World","code":None},
                "seasons":[
                    {
                        "year":2022,"start":"2021-03-01","end":"2022-03-30","current":False,
                        "coverage":{
                            "fixtures":{
                                "events":True,"lineups":True,
                                "statistics_fixtures":True,"statistics_players":True,
                            },
                            "players":True,"injuries":False,
                        },
                    },
                    {
                        "year":2014,"coverage":{"fixtures":{"lineups":True,"statistics_players":True}},
                    },
                ],
            },
            {
                "league":{"id":2,"name":"UEFA Nations League","type":"Cup"},
                "country":{"name":"World","code":None},
                "seasons":[
                    {
                        "year":2024,"start":"2024-09-01","end":"2025-03-31","current":False,
                        "coverage":{
                            "fixtures":{"events":True,"lineups":True,"statistics_players":False},
                            "players":False,"injuries":False,
                        },
                    }
                ],
            },
            {
                "league":{"id":3,"name":"Friendlies Women","type":"Cup"},
                "country":{"name":"World","code":None},
                "seasons":[{"year":2025,"coverage":{"fixtures":{"lineups":True,"statistics_players":True}}}],
            },
            {
                "league":{"id":4,"name":"Club World Cup","type":"Cup"},
                "country":{"name":"World","code":None},
                "seasons":[{"year":2025,"coverage":{"fixtures":{"lineups":True,"statistics_players":True}}}],
            },
            {
                "league":{"id":5,"name":"Premier League","type":"League"},
                "country":{"name":"England","code":"GB"},
                "seasons":[{"year":2025,"coverage":{"fixtures":{"lineups":True,"statistics_players":True}}}],
            },
            {
                "league":{"id":6,"name":"Africa Cup of Nations","type":"Cup"},
                "country":{"name":"World","code":None},
                "seasons":[
                    {
                        "year":2023,
                        "coverage":{
                            "fixtures":{"events":True,"lineups":False,"statistics_players":True},
                            "players":True,
                        },
                    }
                ],
            },
        ]
    }


class FakeBroker:
    def __init__(self,payload):
        self.payload=payload
        self.calls=[]

    def get(self,path,params,**kwargs):
        self.calls.append((path,dict(params),dict(kwargs)))
        return self.payload

    def stats(self):
        return {
            "real_api_calls":1,
            "logical_requests":1,
            "archive_enabled":True,
            "archive_backend":"S3",
            "archive_observations":1,
            "archive_errors":0,
        }


class InternationalDutyProviderCatalogTests(unittest.TestCase):
    def test_qualification_family_precedes_parent_competition(self):
        family,reason=c.classify_candidate("World Cup - Qualification Africa")
        self.assertEqual(family,"WORLD_CUP_QUALIFICATION")
        self.assertIn("WORLD_CUP_QUALIFICATION",reason)

    def test_excludes_women_youth_and_club_competitions(self):
        self.assertIsNone(c.classify_candidate("Friendlies Women")[0])
        self.assertIsNone(c.classify_candidate("World Cup U20")[0])
        self.assertIsNone(c.classify_candidate("Club World Cup")[0])
        self.assertIsNone(c.classify_candidate("Arab Club Champions Cup")[0])

    def test_normalize_preserves_direct_coverage_without_callup_inference(self):
        rows,diag=c.normalize_payload(payload(),2017,2026)
        by={(r["provider_league_id"],r["season"]):r for r in rows}
        self.assertEqual(diag["provider_competitions_seen"],6)
        self.assertEqual(diag["candidate_competitions"],3)
        self.assertEqual(len(rows),3)
        wc=by[("1",2022)]
        self.assertEqual(wc["candidate_family"],"WORLD_CUP_QUALIFICATION")
        self.assertEqual(wc["coverage_lineups"],"true")
        self.assertEqual(wc["coverage_player_statistics"],"true")
        self.assertEqual(wc["direct_matchday_squad_evidence_possible"],"true")
        self.assertEqual(wc["direct_minutes_evidence_possible"],"true")
        self.assertEqual(wc["historical_callup_evidence_possible"],"false")
        self.assertEqual(wc["nationality_inference_allowed"],"false")
        nations=by[("2",2024)]
        self.assertEqual(nations["direct_matchday_squad_evidence_possible"],"true")
        self.assertEqual(nations["direct_minutes_evidence_possible"],"false")
        afcon=by[("6",2023)]
        self.assertEqual(afcon["direct_matchday_squad_evidence_possible"],"true")
        self.assertEqual(afcon["direct_minutes_evidence_possible"],"true")

    def test_out_of_range_seasons_are_excluded(self):
        rows,_=c.normalize_payload(payload(),2024,2026)
        self.assertEqual({int(r["season"]) for r in rows},{2024})

    def test_run_is_one_provider_call_and_research_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            broker=FakeBroker(payload())
            meta=c.run(
                root/"catalog.csv",
                root/"meta.json",
                2017,2026,
                broker=broker,
            )
            saved=json.loads((root/"meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["status"],"OK")
            self.assertEqual(meta["provider_calls"],1)
            self.assertEqual(meta["candidate_competitions"],3)
            self.assertGreater(meta["season_rows_with_direct_minutes_evidence_possible"],0)
            self.assertFalse(meta["historical_callup_evidence_possible"])
            self.assertFalse(meta["nationality_inference_allowed"])
            self.assertFalse(meta["operational_betting_authority"])
            self.assertEqual(saved["selection_status"],"CANDIDATE_REVIEW")
            self.assertEqual(broker.calls[0][0],"/leagues")


if __name__=="__main__":
    unittest.main()
