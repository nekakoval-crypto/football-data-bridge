import json
import tempfile
import unittest
from pathlib import Path

from scripts.motivation_foundation_readiness import build_readiness


class MotivationFoundationReadinessTests(unittest.TestCase):
    def write(self, path, payload):
        path.write_text(json.dumps(payload), encoding="utf-8")

    def materialize(self, root, *, exact=False, catalog=False):
        ops = root / "ops"
        config = root / "config"
        ops.mkdir()
        config.mkdir()
        self.write(ops / "stage80_top5_historical_motivation_last_run.json", {
            "status":"OK","output_rows":16111,"league_season_cells":45,
            "no_lookahead":True,"operational_betting_authority":False,
        })
        self.write(ops / "stage80_top5_motivation_market_research_last_run.json", {
            "status":"OK","joined_rows":16111,"promotes_factor":False,
            "operational_betting_authority":False,
        })
        self.write(ops / "stage80_pbk16_historical_table_context_last_run.json", {
            "status":"OK","source_domestic_rows":40989,"output_rows":40989,
            "domestic_league_ids":16,"safe_regular_rows_with_full_table":37400,
            "no_lookahead":True,
            "exact_title_relegation_motivation_allowed":exact,
        })
        self.write(ops / "standings_snapshot_last_run.json", {
            "tracked_leagues":16,"provider_polling":True,
        })
        rivalry_rows = []
        scopes = [
            "ENGLAND","SPAIN","ITALY","GERMANY","FRANCE",
            "AUSTRIA","BELGIUM","DENMARK","LITHUANIA","LATVIA",
            "NETHERLANDS","NORWAY","POLAND","PORTUGAL","TURKEY",
            "SCOTLAND",
        ]

        for index, scope in enumerate(scopes):
            rivalry_rows.append({
                "id":f"TEST_{scope}",
                "rivalry_name":f"Test {scope}",
                "rivalry_type":"RIVALRY",
                "competition_scope":scope,
                "principled_rivalry":True,
                "team_a_aliases":[f"A{index}"],
                "team_b_aliases":[f"B{index}"],
                "rivalry_classes":["HISTORIC_RIVALRY"],
                "derby_label":False,
                "valid_from_season":None,
                "valid_to_season":None,
            })

        self.write(config / "pbk_motivation_rivalries_v1.json", {
            "version":"TEST_RIVALRY_V2",
            "status":(
                "VERIFIED_PBK16_CATALOG"
                if catalog
                else "PARTIAL_VERIFIED_CATALOG"
            ),
            "matching_policy":"EXACT_NORMALIZED_ALIAS_ONLY_NO_FUZZY",
            "coverage":{
                "pbk16_leagues_represented":16,
                "catalog_completeness":(
                    "VERIFIED_BASELINE"
                    if catalog
                    else "PARTIAL"
                ),
                "exhaustiveness":"NON_EXHAUSTIVE_BY_DESIGN",
                "unknown_pair_policy":"UNKNOWN",
            },
            "rivalries":rivalry_rows,
        })
        return ops, config

    def test_current_state_is_in_progress_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ops, config = self.materialize(root)
            report = build_readiness(ops, config)
            self.assertEqual(report["status"], "IN_PROGRESS")
            self.assertEqual(
                report["checklist_item_13_predictive_authority"],
                "NOT_AUTHORIZED",
            )
            self.assertNotIn(
                "PBK16_EXACT_OBJECTIVE_CONTRACTS_INCOMPLETE",
                report["hard_blockers_to_foundation_closure"],
            )
            self.assertIn(
                "RIVALRY_CATALOG_PARTIAL",
                report["hard_blockers_to_foundation_closure"],
            )
            self.assertEqual(report["evidence"]["exact_objective_required_cells"],143)
            self.assertEqual(report["evidence"]["exact_objective_verified_cells"],143)
            self.assertEqual(report["evidence"]["exact_objective_missing_cells"],0)
            self.assertFalse(report["operational_betting_authority"])

    def test_even_with_pbk16_and_catalog_forward_validation_still_blocks_closure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ops, config = self.materialize(root, exact=True, catalog=True)
            report = build_readiness(ops, config)
            self.assertEqual(report["status"], "IN_PROGRESS")
            self.assertIn(
                "FORWARD_MOTIVATION_LABEL_AND_VALIDATION_RAIL_NOT_COMPLETE",
                report["hard_blockers_to_foundation_closure"],
            )


if __name__ == "__main__":
    unittest.main()
