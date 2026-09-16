import copy
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import generic_1x2_probability_v1_gate as gate


class GateTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config" / "pbk_generic_1x2_probability_v1_gate.json").read_text())

    def test_no_vig_and_invalid_prices(self):
        self.assertAlmostEqual(sum(gate.market_probabilities({"B365H": "2", "B365D": "3", "B365A": "4"})), 1.0, places=12)
        with self.assertRaises(ValueError): gate.market_probabilities({"B365H": "1", "B365D": "3", "B365A": "4"})

    def test_invalid_probability_is_rejected(self):
        with self.assertRaises(ValueError): gate.shifted_probabilities((0.5, 0.5, 0.0), 0.0, 0.0)

    def test_mandatory_unknown_is_fail(self):
        result = gate.finalize({}, self.config, Path("missing.csv"), None, 0, False)
        self.assertEqual(result["overall_status"], "FAIL")

    def test_wrong_sha_and_missing_source_fail_closed(self):
        result = gate.failed_missing_source(Path("missing.csv"), self.config)
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertFalse(result["test_labels_read"])

    def test_deterministic_fit(self):
        rows = [((0.4, 0.3, 0.3), "H")] * 4 + [((0.4, 0.3, 0.3), "D")] * 3 + [((0.4, 0.3, 0.3), "A")] * 2
        self.assertEqual(gate.fit_train(rows), gate.fit_train(rows))

    def write_source(self, rows, headers=None):
        headers = headers or ["match_id", "season", "Div", "FTR", "B365H", "B365D", "B365A", "source_url"]
        temporary = tempfile.NamedTemporaryFile(mode="w", newline="", suffix=".csv", delete=False, encoding="utf-8")
        with temporary as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader(); writer.writerows(rows)
        return Path(temporary.name)

    def miniature_config(self, source):
        config = copy.deepcopy(self.config)
        config["expected_source"].update({
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "rows": 5, "columns": 8,
            "seasons": ["2018/19", "2019/20", "2020/21", "2021/22", "2023/24"],
            "divisions": ["E0"], "unique_source_urls": 1,
        })
        config["train_seasons"] = ["2019/20", "2020/21", "2021/22"]
        config["test_seasons"] = ["2023/24"]
        return config

    def rows(self):
        base = {"Div": "E0", "B365H": "2", "B365D": "3", "B365A": "4", "source_url": "u"}
        return [dict(base, match_id="old", season="2018/19", FTR="H"), dict(base, match_id="h", season="2019/20", FTR="H"), dict(base, match_id="d", season="2020/21", FTR="D"), dict(base, match_id="a", season="2021/22", FTR="A"), dict(base, match_id="test", season="2023/24", FTR="")]

    def test_target_feature_fails_leakage_guard(self):
        source = self.write_source(self.rows())
        config = self.miniature_config(source)
        config["allowed_feature_columns"].append("FTR")
        result = gate.run_gate(source, config)
        self.assertEqual(result["gate_checks"]["LEAKAGE/NO-LOOKAHEAD"]["status"], "FAIL")
        self.assertEqual(result["overall_status"], "FAIL")

    def test_future_feature_fails_leakage_guard(self):
        source = self.write_source(self.rows())
        config = self.miniature_config(source)
        config["allowed_feature_columns"].append("post_kickoff_information")
        result = gate.run_gate(source, config)
        self.assertEqual(result["gate_checks"]["LEAKAGE/NO-LOOKAHEAD"]["status"], "FAIL")
        self.assertEqual(result["research_status"], "PREREGISTERED_DATA_REQUIRED")

    def test_missing_source_blocks_test(self):
        result = gate.run_gate(Path("does-not-exist.csv"), self.config)
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertEqual(result["research_status"], "PREREGISTERED_DATA_REQUIRED")

    def test_wrong_shape_schema_and_duplicate_match_id_fail(self):
        source = self.write_source(self.rows())
        config = self.miniature_config(source)
        config["expected_source"]["columns"] = 9
        self.assertEqual(gate.run_gate(source, config)["overall_status"], "FAIL")
        source = self.write_source(self.rows()[:-1] + [dict(self.rows()[-1], match_id="a")])
        config = self.miniature_config(source)
        self.assertEqual(gate.run_gate(source, config)["gate_checks"]["SOURCE_COVERAGE"]["status"], "FAIL")

    def test_b365_missing_is_excluded_without_fallback(self):
        rows = self.rows(); rows[1]["B365H"] = ""
        source = self.write_source(rows)
        result = gate.run_gate(source, self.miniature_config(source))
        detail = result["gate_checks"]["B365_FILTER"]
        self.assertEqual(detail["excluded_missing_b365"], 1)
        self.assertEqual(detail["fallback_bookmaker"], "FORBIDDEN")

    def test_split_overlap_fails(self):
        source = self.write_source(self.rows())
        config = self.miniature_config(source); config["test_seasons"] = ["2021/22", "2023/24"]
        self.assertEqual(gate.run_gate(source, config)["gate_checks"]["SPLIT_INTEGRITY"]["status"], "FAIL")

    def test_unexpected_season_fails_source_coverage(self):
        rows = self.rows(); rows[0]["season"] = "2017/18"
        source = self.write_source(rows)
        result = gate.run_gate(source, self.miniature_config(source))
        self.assertEqual(result["gate_checks"]["SOURCE_COVERAGE"]["status"], "FAIL")

    def test_missing_required_column_fails_schema(self):
        headers = ["match_id", "season", "Div", "B365H", "B365D", "B365A", "source_url"]
        rows = [{key: value for key, value in row.items() if key in headers} for row in self.rows()]
        source = self.write_source(rows, headers)
        result = gate.run_gate(source, self.miniature_config(source))
        self.assertEqual(result["gate_checks"]["REQUIRED_SCHEMA"]["status"], "FAIL")

    def test_probability_sum_failure_fails_guards(self):
        source = self.write_source(self.rows())
        with patch.object(gate, "shifted_probabilities", return_value=(0.3, 0.3, 0.3)):
            result = gate.run_gate(source, self.miniature_config(source))
        self.assertEqual(result["gate_checks"]["PROBABILITY_GUARDS"]["status"], "FAIL")
        self.assertEqual(result["overall_status"], "FAIL")

    def test_deterministic_mismatch_fails(self):
        source = self.write_source(self.rows())
        first = {"alpha_h": 0.0, "alpha_d": 0.0, "alpha_a": 0.0, "train_logloss": 1.0}
        second = {"alpha_h": 0.1, "alpha_d": 0.0, "alpha_a": 0.0, "train_logloss": 1.0}
        with patch.object(gate, "fit_train", side_effect=[first, second]):
            result = gate.run_gate(source, self.miniature_config(source))
        self.assertEqual(result["gate_checks"]["DETERMINISM"]["status"], "FAIL")
        self.assertEqual(result["overall_status"], "FAIL")

    def test_wrong_sha_fails(self):
        source = self.write_source(self.rows())
        config = self.miniature_config(source); config["expected_source"]["sha256"] = "0" * 64
        self.assertEqual(gate.run_gate(source, config)["gate_checks"]["SOURCE_IDENTITY"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()

