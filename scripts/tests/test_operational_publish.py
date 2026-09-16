import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publish_operational_commit import publish


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote.git'
        self.run_git(self.root, 'init', '--bare', str(self.remote))
        self.a, self.b = self.root / 'a', self.root / 'b'
        self.run_git(self.root, 'clone', str(self.remote), str(self.a))
        self.config(self.a)
        self.run_git(self.a, 'checkout', '-b', 'main')
        self.commit(self.a, 'shared.txt', 'initial\n')
        self.run_git(self.a, 'push', 'origin', 'main')
        self.run_git(self.root, 'clone', '-b', 'main', str(self.remote), str(self.b))
        self.config(self.b)
        self.env = patch.dict(os.environ, {'GITHUB_REF': 'refs/heads/main'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_git(self, cwd, *args):
        return subprocess.check_output(['git', *args], cwd=cwd, stderr=subprocess.STDOUT, text=True).strip()

    def config(self, cwd):
        self.run_git(cwd, 'config', 'user.name', 'Test')
        self.run_git(cwd, 'config', 'user.email', 'test@example.invalid')

    def commit(self, cwd, name, text):
        (cwd / name).write_text(text)
        self.run_git(cwd, 'add', name)
        self.run_git(cwd, 'commit', '-m', name)

    def test_concurrent_unrelated_commit_survives(self):
        self.commit(self.a, 'a.txt', 'snapshot\n')
        self.commit(self.b, 'b.txt', 'other workflow\n')
        self.run_git(self.b, 'push', 'origin', 'main')
        publish(self.a, pause=lambda _: None)
        self.run_git(self.b, 'pull', '--ff-only', 'origin', 'main')
        self.assertEqual((self.b / 'a.txt').read_text(), 'snapshot\n')
        self.assertEqual((self.b / 'b.txt').read_text(), 'other workflow\n')

    def test_conflicting_snapshot_is_not_overwritten(self):
        self.commit(self.a, 'shared.txt', 'snapshot A\n')
        original = self.run_git(self.a, 'rev-parse', 'HEAD')
        self.commit(self.b, 'shared.txt', 'snapshot B\n')
        self.run_git(self.b, 'push', 'origin', 'main')
        with self.assertRaisesRegex(RuntimeError, 'conflict'):
            publish(self.a, pause=lambda _: None)
        self.assertEqual(self.run_git(self.a, 'rev-parse', 'HEAD'), original)
        self.assertEqual((self.a / 'shared.txt').read_text(), 'snapshot A\n')
        self.assertEqual(self.run_git(self.a, 'show', 'origin/main:shared.txt'), 'snapshot B')

    def test_feature_dispatch_cannot_publish(self):
        with patch.dict(os.environ, {'GITHUB_REF': 'refs/heads/feature'}):
            with self.assertRaisesRegex(RuntimeError, 'requires'):
                publish(self.a)

    def test_generic_1x2_forward_writers_share_safe_publish_contract(self):
        repo = Path(__file__).resolve().parents[2]
        workflow_paths = [
            repo / '.github/workflows/stage71j-shared-core-market-capture.yml',
            repo / '.github/workflows/stage71-live-snapshot.yml',
        ]
        for path in workflow_paths:
            text = path.read_text(encoding='utf-8')
            self.assertIn('group: pbk-generic-1x2-forward-writers-${{ github.ref }}', text)
            self.assertIn('cancel-in-progress: false', text)
            self.assertIn('fetch-depth: 0', text)
            self.assertIn('python scripts/publish_operational_commit.py', text)
            self.assertIn('if: always()', text)
            self.assertNotIn('git pull --rebase origin main', text)
            self.assertNotIn('git push origin main || true', text)


if __name__ == '__main__':
    unittest.main()
