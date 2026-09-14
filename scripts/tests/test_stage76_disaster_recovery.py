import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage76_disaster_recovery as dr


class Stage76DisasterRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'ops').mkdir()
        (self.root / 'config').mkdir()
        (self.root / 'ops' / 'forward_log.csv').write_text('id,status\n1,OPEN\n', encoding='utf-8')
        (self.root / 'ops' / 'stage71_observation_state.json').write_text('{"api_day_calls":12}\n', encoding='utf-8')
        (self.root / 'ops' / 'standings_snapshots.csv').write_text('snapshot_id,team_id\ns1,10\n', encoding='utf-8')
        (self.root / 'config' / 'pbk.json').write_text('{"enabled":true}\n', encoding='utf-8')
        (self.root / 'config' / 'provider_secret.json').write_text('{"value":"never-copy"}\n', encoding='utf-8')
        (self.root / 'ops' / 'binary.bin').write_bytes(b'not-allowed')
        self.pack = self.root / 'pack'

    def tearDown(self):
        self.temp.cleanup()

    def create(self):
        return dr.create_pack(self.root, self.pack, repository_sha='abc123', replace=False)

    def test_create_pack_is_allowlisted_and_content_addressed(self):
        manifest = self.create()
        paths = {item['path'] for item in manifest['files']}
        self.assertIn('ops/forward_log.csv', paths)
        self.assertIn('ops/stage71_observation_state.json', paths)
        self.assertIn('config/pbk.json', paths)
        self.assertNotIn('config/provider_secret.json', paths)
        self.assertNotIn('ops/binary.bin', paths)
        self.assertEqual(manifest['required_recovery_files']['ops/forward_log.csv'], 'PRESENT')
        self.assertEqual(manifest['required_recovery_files']['ops/stage71_observation_state.json'], 'PRESENT')
        self.assertEqual(manifest['derived_data_policy']['stage72_sqlite'], 'EXCLUDED_REBUILDABLE')
        result = dr.verify_pack(self.pack)
        self.assertEqual(result['status'], 'OK')
        self.assertEqual(result['manifest_files'], 4)

    def test_tampered_payload_is_rejected_before_restore(self):
        self.create()
        (self.pack / 'payload' / 'ops' / 'forward_log.csv').write_text('tampered\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            dr.verify_pack(self.pack)
        with self.assertRaises(ValueError):
            dr.restore_pack(self.pack, self.root / 'restore', apply=True)

    def test_tampered_manifest_is_rejected(self):
        self.create()
        manifest = json.loads((self.pack / 'manifest.json').read_text(encoding='utf-8'))
        manifest['repository_sha'] = 'forged'
        (self.pack / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaises(ValueError):
            dr.verify_pack(self.pack)

    def test_dry_run_never_writes_target(self):
        self.create()
        target = self.root / 'restore'
        result = dr.restore_pack(self.pack, target, apply=False)
        self.assertEqual(result['status'], 'DRY_RUN')
        self.assertEqual(result['restored'], 0)
        self.assertGreater(result['missing'], 0)
        self.assertFalse(target.exists())

    def test_apply_restores_missing_files_without_deleting_extras(self):
        self.create()
        target = self.root / 'restore'
        target.mkdir()
        extra = target / 'ops' / 'local_only.txt'
        extra.parent.mkdir(parents=True)
        extra.write_text('keep me', encoding='utf-8')
        result = dr.restore_pack(self.pack, target, apply=True)
        self.assertEqual(result['status'], 'APPLIED')
        self.assertEqual((target / 'ops' / 'forward_log.csv').read_text(encoding='utf-8'), 'id,status\n1,OPEN\n')
        self.assertTrue(extra.exists())
        self.assertFalse(result['deletes_files'])

    def test_existing_different_file_requires_explicit_overwrite(self):
        self.create()
        target = self.root / 'restore'
        destination = target / 'ops' / 'forward_log.csv'
        destination.parent.mkdir(parents=True)
        destination.write_text('newer local data\n', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            dr.restore_pack(self.pack, target, apply=True)
        self.assertEqual(destination.read_text(encoding='utf-8'), 'newer local data\n')
        result = dr.restore_pack(self.pack, target, apply=True, allow_overwrite=True)
        self.assertGreaterEqual(result['overwritten'], 1)
        self.assertEqual(destination.read_text(encoding='utf-8'), 'id,status\n1,OPEN\n')

    def test_path_traversal_manifest_entry_is_rejected_even_with_valid_manifest_hash(self):
        self.create()
        manifest_path = self.pack / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['files'][0]['path'] = '../outside.txt'
        raw = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')
        manifest_path.write_bytes(raw)
        import hashlib
        (self.pack / 'manifest.sha256').write_text(hashlib.sha256(raw).hexdigest() + '  manifest.json\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            dr.verify_pack(self.pack)

    def test_create_refuses_to_replace_existing_pack_without_flag(self):
        self.create()
        with self.assertRaises(FileExistsError):
            dr.create_pack(self.root, self.pack, repository_sha='abc123')
        manifest = dr.create_pack(self.root, self.pack, repository_sha='def456', replace=True)
        self.assertEqual(manifest['repository_sha'], 'def456')


if __name__ == '__main__':
    unittest.main()
