import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage67_health_policy as policy


class Stage67HealthPolicyTests(unittest.TestCase):
    def write(self, root, name, payload):
        (root / name).write_text(json.dumps(payload), encoding="utf-8")

    def base_health(self):
        return {
            "generated_at_utc": "2026-09-14T12:00:00Z",
            "status": "CRITICAL",
            "summary": {"critical_issues": 2, "warnings": 2, "stage72_integrity": "ok"},
            "stage_health": [],
            "issues": [
                {"severity": "CRITICAL", "code": "MISSING_STABLE_SOURCES", "message": "Stage72 missing=['standings_snapshots.csv']"},
                {"severity": "CRITICAL", "code": "STAGE72_MISSING_STABLE_SOURCE", "message": "Stage72 missing stable sources: standings_snapshots.csv"},
                {"severity": "WARN", "code": "SCHEMA_VERSION", "message": "Expected Stage72 schema v6, got 13"},
                {"severity": "WARN", "code": "STALE_STAGE", "message": "Stage71H readiness is stale"},
            ],
        }

    def test_optional_standings_and_matching_schema_do_not_make_health_critical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "system_health.json", self.base_health())
            self.write(root, "stage72_last_run.json", {"schema_version": "13", "missing_stable_sources": ["standings_snapshots.csv"]})
            self.write(root, "stage72_schema.json", {"schema_version": "13"})
            self.write(root, "stage67_last_run.json", {})
            result = policy.reconcile(root)
            self.assertEqual(result["status"], "WARN")
            self.assertEqual(result["summary"]["critical_issues"], 0)
            self.assertEqual(result["summary"]["warnings"], 1)
            self.assertEqual(result["summary"]["optional_stable_sources_pending"], ["standings_snapshots.csv"])
            self.assertEqual([x["code"] for x in result["issues"]], ["STALE_STAGE"])

    def test_required_missing_source_remains_critical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "system_health.json", self.base_health())
            self.write(root, "stage72_last_run.json", {"schema_version": "13", "missing_stable_sources": ["standings_snapshots.csv", "user_forward_view.csv"]})
            self.write(root, "stage72_schema.json", {"schema_version": "13"})
            self.write(root, "stage67_last_run.json", {})
            result = policy.reconcile(root)
            self.assertEqual(result["status"], "CRITICAL")
            issue = next(x for x in result["issues"] if x["code"] == "STAGE72_MISSING_STABLE_SOURCE")
            self.assertIn("user_forward_view.csv", issue["message"])
            self.assertNotIn("standings_snapshots.csv", issue["message"])

    def test_schema_manifest_mismatch_is_warning(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            health = self.base_health()
            health["issues"] = []
            self.write(root, "system_health.json", health)
            self.write(root, "stage72_last_run.json", {"schema_version": "12", "missing_stable_sources": []})
            self.write(root, "stage72_schema.json", {"schema_version": "13"})
            self.write(root, "stage67_last_run.json", {})
            result = policy.reconcile(root)
            self.assertEqual(result["status"], "WARN")
            self.assertEqual(result["issues"][0]["code"], "SCHEMA_VERSION")
            self.assertIn("v13", result["issues"][0]["message"])


if __name__ == "__main__":
    unittest.main()
