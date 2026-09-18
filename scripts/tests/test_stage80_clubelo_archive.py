import unittest

from scripts.stage80_clubelo_archive import build, merge_rows, normalize_text


class Stage80ClubEloArchiveTests(unittest.TestCase):
    def test_normalizes_daily_snapshot(self):
        text=(
            "Rank,Club,Country,Level,Elo,From,To\n"
            "1,Arsenal,ENG,1,2067.123,2026-09-15,2026-09-18\n"
            "2,Bayern,GER,1,2014.5,2026-09-14,2026-09-18\n"
        )
        rows,invalid,columns=normalize_text(
            text,"2026-09-18","2026-09-18T12:00:00Z","https://api.clubelo.com/2026-09-18"
        )
        self.assertEqual(invalid,0)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["club"],"Arsenal")
        self.assertEqual(rows[0]["elo"],"2067.123")
        self.assertEqual(rows[0]["historical_enrichment_only"],"true")
        self.assertEqual(rows[0]["probability_mutation"],"false")
        self.assertIn("Elo",columns)

    def test_same_snapshot_is_idempotent_first_observation_wins(self):
        original=[{
            "snapshot_date":"2026-09-18","observed_at_utc":"2026-09-18T12:00:00Z",
            "club":"Arsenal","country":"ENG","elo":"2000",
        }]
        incoming=[{
            "snapshot_date":"2026-09-18","observed_at_utc":"2026-09-18T13:00:00Z",
            "club":"Arsenal","country":"ENG","elo":"2100",
        }]
        result=merge_rows(original,incoming)
        self.assertEqual(result["added_rows"],0)
        self.assertEqual(result["duplicate_incoming_rows"],1)
        self.assertEqual(result["rows"][0]["elo"],"2000")

    def test_build_adds_new_day_for_same_club(self):
        existing=[{
            "snapshot_date":"2026-09-17","observed_at_utc":"2026-09-17T12:00:00Z",
            "club":"Arsenal","country":"ENG","elo":"2000",
        }]
        text="Rank,Club,Country,Level,Elo,From,To\n1,Arsenal,ENG,1,2005,2026-09-18,2026-09-18\n"
        result=build(
            "2026-09-18","2026-09-18T12:00:00Z",existing,text,
            "https://api.clubelo.com/2026-09-18",
        )
        self.assertEqual(result["added_rows"],1)
        self.assertEqual(len(result["rows"]),2)

    def test_invalid_rows_are_not_zero_filled(self):
        text="Rank,Club,Country,Level,Elo,From,To\n1,Arsenal,ENG,1,,2026-09-18,2026-09-18\n"
        rows,invalid,_=normalize_text(
            text,"2026-09-18","2026-09-18T12:00:00Z","https://api.clubelo.com/2026-09-18"
        )
        self.assertEqual(rows,[])
        self.assertEqual(invalid,1)


if __name__=="__main__":
    unittest.main()
