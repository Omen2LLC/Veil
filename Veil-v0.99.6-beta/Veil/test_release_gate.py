from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from release_gate import check_record


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = Path(__file__).parent
        shutil.copytree(source / 'compatibility', self.root / 'compatibility')
        shutil.copyfile(source / 'compatibility_profiles.json', self.root / 'compatibility_profiles.json')
        self.now = datetime.now(timezone.utc)
        for edition in ('studio', 'free'):
            path = self.root / 'compatibility' / f'latest_windows_{edition}.json'
            record = json.loads(path.read_text())
            record.update(veil_version='v0.99.3-beta', checked_at_utc=self.now.isoformat())
            path.write_text(json.dumps(record))

    def test_both_editions_are_reported(self):
        result = check_record('v0.99.3-beta', self.root, self.now)
        self.assertEqual(result.get('latest_windows_free_build'), '21.1.1.10')

    def test_missing_free_native_evidence_blocks_release(self):
        (self.root / 'compatibility/verified/21.1.1.10-free.json').unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            check_record('v0.99.3-beta', self.root, self.now)

    def test_unverified_free_profile_blocks_release(self):
        path = self.root / 'compatibility_profiles.json'
        profiles = json.loads(path.read_text())
        profiles['21.1.1.10-free']['native_verified'] = False
        path.write_text(json.dumps(profiles))
        with self.assertRaises(ValueError):
            check_record('v0.99.3-beta', self.root, self.now)

    def test_stale_free_metadata_blocks_release(self):
        path = self.root / 'compatibility/latest_windows_free.json'
        record = json.loads(path.read_text())
        record['checked_at_utc'] = '2020-01-01T00:00:00+00:00'
        path.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            check_record('v0.99.3-beta', self.root, self.now)


if __name__ == '__main__':
    unittest.main()
