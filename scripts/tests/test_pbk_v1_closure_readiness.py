import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pbk_v1_closure_readiness as gate


class ClosureReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ops = self.root / 'ops'
        self.ops.mkdir(parents=True)
        for rel in gate.REQUIRED_FILES:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# placeholder\n', encoding='utf-8')
        (self.root/'app/sw.js').write_text(
            "const CACHE='pbk-shell-v15';\nif(u.pathname.startsWith('/api/')) fetch(e.request,{cache:'no-store'});\n",
            encoding='utf-8')
        (self.root/'scripts/stage72_build_data_layer.py').write_text("SCHEMA_VERSION='14'\n", encoding='utf-8')
        (self.root/'scripts/stage73_internal_api.py').write_text(
            "'/v1/match-card' '/v1/rounds/current' '/v1/motivation'\n", encoding='utf-8')
        for rel in (
            '.github/workflows/stage75-probability-value.yml',
            '.github/workflows/standings-snapshot.yml',
            '.github/workflows/pbk-v1-production-acceptance.yml',
        ):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('python scripts/publish_operational_commit.py\n', encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, name, payload):
        (self.ops/name).write_text(json.dumps(payload), encoding='utf-8')

    def seed_performance(self, forward_roi=-21.0, watch_roi=-61.6):
        self.write_json('forward_performance.json', {
            'status':'OK','scope':'clean prospective canonical forward only',
            'overall':{'rows':3,'settled_rows':2,'user_execution_coverage_pct':100.0,'user_roi_pct':forward_roi},
            'policy':{'historical_backfill':'forbidden'},
        })
        self.write_json('watch_performance.json', {
            'status':'OK','scope':'prospective research WATCH crossings only',
            'overall':{'crossings':12,'settled':10,'user_roi_pct':watch_roi},
            'policy':{'canonical_forward':'unchanged','historical_backfill':'forbidden'},
        })

    def test_negative_real_performance_does_not_block_technical_closure(self):
        self.seed_performance(-99.0, -88.0)
        checks = gate.performance_checks(self.ops)
        self.assertEqual([item['status'] for item in checks], ['PASS','PASS'])
        for item in checks:
            self.assertFalse(item['evidence']['profitability_required_for_closure'])

    def test_production_acceptance_waiting_keeps_final_gate_waiting(self):
        self.seed_performance()
        self.write_json('pbk_v1_production_acceptance.json', {
            'status':'WAITING','ready_to_close':False,'hard_failure':False,
            'roadmap_4_today_live':{'status':'WAITING'},
            'roadmap_5_standings_motivation':{'status':'WAITING'},
        })
        payload = gate.evaluate(self.root, self.ops)
        self.assertEqual(payload['status'], 'WAITING')
        self.assertFalse(payload['ready_for_manual_close'])
        self.assertFalse(payload['hard_failure'])
        self.assertEqual(payload['real_performance']['status'], 'PASS')
        self.assertEqual(payload['static_hygiene']['status'], 'PASS')

    def test_ready_requires_production_performance_and_static_hygiene(self):
        self.seed_performance()
        self.write_json('pbk_v1_production_acceptance.json', {
            'status':'PASS','ready_to_close':True,'hard_failure':False,
            'roadmap_4_today_live':{'status':'PASS'},
            'roadmap_5_standings_motivation':{'status':'PASS'},
        })
        payload = gate.evaluate(self.root, self.ops)
        self.assertEqual(payload['status'], 'READY')
        self.assertTrue(payload['ready_for_manual_close'])
        self.assertFalse(payload['policy']['automatic_pbk_close'])
        self.assertEqual(payload['policy']['provider_calls'], 0)

    def test_direct_provider_or_legacy_frontend_endpoint_is_hard_failure(self):
        self.seed_performance()
        self.write_json('pbk_v1_production_acceptance.json', {
            'status':'PASS','ready_to_close':True,'hard_failure':False,
        })
        (self.root/'app/today-live.js').write_text(
            "fetch('https://v3.football.api-sports.io/fixtures'); fetch('/v1/match?fixture_id=1');",
            encoding='utf-8')
        payload = gate.evaluate(self.root, self.ops)
        self.assertEqual(payload['status'], 'FAIL')
        self.assertTrue(payload['hard_failure'])
        frontend = next(x for x in payload['static_hygiene']['checks'] if x['code']=='FRONTEND_PROVIDER_ISOLATION')
        self.assertEqual(frontend['status'], 'FAIL')
        self.assertGreaterEqual(len(frontend['evidence']['violations']), 2)

    def test_schema_or_publisher_regression_is_hard_failure(self):
        self.seed_performance()
        self.write_json('pbk_v1_production_acceptance.json', {
            'status':'PASS','ready_to_close':True,'hard_failure':False,
        })
        (self.root/'scripts/stage72_build_data_layer.py').write_text("SCHEMA_VERSION='6'\n", encoding='utf-8')
        (self.root/'.github/workflows/standings-snapshot.yml').write_text('git push origin main\n', encoding='utf-8')
        payload = gate.evaluate(self.root, self.ops)
        self.assertEqual(payload['status'], 'FAIL')
        statuses = {x['code']:x['status'] for x in payload['static_hygiene']['checks']}
        self.assertEqual(statuses['STAGE72_SCHEMA_BASELINE'], 'FAIL')
        self.assertEqual(statuses['CANONICAL_OPERATIONAL_PUBLISHER'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
