import unittest
from scripts import stage80_international_duty_pbk16_club_identity as c


def temporal(name="Man City", status="BOUNDED_CHAIN_CONFIRMED"):
    return [{
        "fixture_id":"1","kickoff_utc":"2025-11-01T12:00:00Z",
        "player_id":"10","player_name":"P","temporal_club_status":status,
        "transfermarkt_club_id":"281","transfermarkt_club_name":name,
    }]


def leagues():
    return [{"api_league_id":"39","resolved":"YES"}]


def fixture(home="Manchester City", home_id="50", league="39"):
    return [{
        "provider_league_id":league,
        "home_team":home,
        "home_team_logo_url":f"https://media.api-sports.io/football/teams/{home_id}.png",
        "away_team":"Other",
        "away_team_logo_url":"https://media.api-sports.io/football/teams/99.png",
    }]


class Pbk16ClubIdentityTests(unittest.TestCase):
    def test_explicit_alias_unique_maps(self):
        rows=c.build(temporal("Man City"),leagues(),fixture())
        self.assertEqual(rows[0]["pbk16_club_identity_status"],"PBK16_EXACT_ALIAS_UNIQUE")
        self.assertEqual(rows[0]["pbk16_team_id"],"50")

    def test_diacritic_normalization_maps(self):
        rows=c.build(temporal("Widzew Lodz"),leagues(),fixture("Widzew Łódź","6962"))
        self.assertEqual(rows[0]["pbk16_team_id"],"6962")

    def test_outside_pbk16_fails_closed(self):
        rows=c.build(temporal("Colo-Colo"),leagues(),fixture())
        self.assertEqual(rows[0]["pbk16_club_identity_status"],"OUTSIDE_PBK16_OR_UNMAPPED")
        self.assertEqual(rows[0]["pbk16_team_id"],"")

    def test_non_bounded_rows_are_excluded(self):
        self.assertEqual(c.build(temporal("Man City","UNBOUNDED_INTERVAL"),leagues(),fixture()),[])

    def test_team_stats_extend_pbk16_catalog_without_provider_call(self):
        stats=[{
            "provider_league_id":"39",
            "team_id":"39",
            "team_name":"Wolverhampton",
        }]
        rows=c.build(temporal("Wolves"),leagues(),[],stats)
        self.assertEqual(rows[0]["pbk16_club_identity_status"],"PBK16_EXACT_ALIAS_UNIQUE")
        self.assertEqual(rows[0]["pbk16_team_id"],"39")

    def test_non_pbk16_league_is_excluded_from_catalog(self):
        rows=c.build(temporal("Man City"),leagues(),fixture(league="999"))
        self.assertEqual(rows[0]["pbk16_club_identity_status"],"OUTSIDE_PBK16_OR_UNMAPPED")

    def test_ambiguous_same_key_fails_closed(self):
        fx=fixture()
        fx.append({
            "provider_league_id":"39",
            "home_team":"Manchester City",
            "home_team_logo_url":"https://media.api-sports.io/football/teams/51.png",
            "away_team":"Other2",
            "away_team_logo_url":"https://media.api-sports.io/football/teams/98.png",
        })
        rows=c.build(temporal("Man City"),leagues(),fx)
        self.assertEqual(rows[0]["pbk16_club_identity_status"],"AMBIGUOUS_PBK16_TEAM")
        self.assertEqual(rows[0]["pbk16_team_id"],"")


if __name__=="__main__":
    unittest.main()
