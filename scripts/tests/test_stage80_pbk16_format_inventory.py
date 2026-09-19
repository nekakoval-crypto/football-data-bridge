import unittest

from scripts import stage80_pbk16_format_inventory as inv


class PBK16FormatInventoryTests(unittest.TestCase):
    def test_round_inventory_detects_split_and_playoff_markers(self):
        rows=[
            {"round":"Regular Season - 1"},
            {"round":"Championship Round - 3"},
            {"round":"Relegation Group - 2"},
            {"round":"Play-Off - Final"},
        ]
        labels,markers,marker_labels=inv.round_inventory(rows)
        self.assertEqual(len(labels),4)
        self.assertIn("CHAMPIONSHIP",markers)
        self.assertIn("RELEGATION",markers)
        self.assertIn("PLAYOFF",markers)
        self.assertEqual(len(marker_labels),3)

    def test_balanced_single_table_candidate(self):
        rows=[
            {"status":"FT","home_team_id":"1","away_team_id":"2"},
            {"status":"FT","home_team_id":"2","away_team_id":"1"},
        ]
        archive=inv.appearances(rows)
        finished=inv.appearances(rows,finished_only=True)
        cls=inv.structural_class(
            available=True,rows=rows,phase_markers=[],
            archive_counts=archive,finished_counts=finished,
        )
        self.assertEqual(cls,"BALANCED_SINGLE_TABLE_CANDIDATE")

    def test_phase_marker_blocks_naive_single_table_class(self):
        rows=[{"status":"FT","home_team_id":"1","away_team_id":"2"}]
        cls=inv.structural_class(
            available=True,rows=rows,phase_markers=["CHAMPIONSHIP"],
            archive_counts=inv.appearances(rows),
            finished_counts=inv.appearances(rows,finished_only=True),
        )
        self.assertEqual(cls,"PHASED_OR_SPLIT_CANDIDATE")

    def test_unavailable_provider_season_is_explicit(self):
        cls=inv.structural_class(
            available=False,rows=[],phase_markers=[],
            archive_counts={},finished_counts={},
        )
        self.assertEqual(cls,"UNAVAILABLE_PROVIDER_SEASON")

    def test_full_16x9_grid_is_preserved(self):
        state=[]
        archive=[]
        countries=[f"C{i:02d}" for i in range(16)]
        fixture_id=1
        for ci,country in enumerate(countries):
            for season in inv.EXPECTED_SEASONS:
                unavailable=(country=="C00" and season==2017)
                state.append({
                    "competition_role":"DOMESTIC_LEAGUE",
                    "country":country,
                    "provider_competition_id":str(100+ci),
                    "competition_name":f"League {ci}",
                    "season":str(season),
                    "provider_season_available":"false" if unavailable else "true",
                    "status":"UNAVAILABLE_PROVIDER_SEASON" if unavailable else "CAPTURED",
                    "provider_fixture_rows":"0" if unavailable else "2",
                })
                if unavailable:
                    continue
                for h,a in (("1","2"),("2","1")):
                    archive.append({
                        "fixture_id":str(fixture_id),
                        "competition_role":"DOMESTIC_LEAGUE",
                        "country":country,"season":str(season),
                        "round":"Regular Season - 1",
                        "status":"FT","home_team_id":h,"away_team_id":a,
                    })
                    fixture_id+=1
        rows=inv.build(state,archive)
        self.assertEqual(len(rows),144)
        self.assertEqual(sum(r["backfill_status"]=="CAPTURED" for r in rows),143)
        self.assertEqual(sum(r["backfill_status"]=="UNAVAILABLE_PROVIDER_SEASON" for r in rows),1)
        self.assertTrue(all(r["exact_motivation_contract_status"]=="UNVERIFIED" for r in rows))
        self.assertTrue(all(r["operational_betting_authority"]=="false" for r in rows))

    def test_duplicate_state_cell_is_rejected(self):
        row={
            "competition_role":"DOMESTIC_LEAGUE","country":"England","season":"2024"
        }
        with self.assertRaises(ValueError):
            inv.domestic_state_cells([row,row])


if __name__=="__main__":
    unittest.main()
