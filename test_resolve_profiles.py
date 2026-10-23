import copy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import resolve_profiles


class ProfileSelectionTests(unittest.TestCase):
    def setUp(self):
        self.studio = json.loads(Path(__file__).with_name('compatibility_profiles.json').read_text())['21.1.1.10']
        self.free = copy.deepcopy(self.studio)
        self.free.update(edition='free', executable_sha256='f' * 64)
        self.profiles = {'21.1.1.10': self.studio, '21.1.1.10-free': self.free}

    def select(self, digest, version='21.1.1.10'):
        return resolve_profiles.select_profile(self.profiles, version, digest, {'21.1.1.10'})

    def test_same_version_selects_each_executable_independently(self):
        self.assertIs(self.select(self.studio['executable_sha256']), self.studio)
        self.assertIs(self.select('f' * 64), self.free)

    def test_unknown_executable_is_blocked(self):
        with self.assertRaisesRegex(RuntimeError, 'No verified.*executable'):
            self.select('a' * 64)

    def test_unverified_candidate_is_blocked(self):
        self.free['native_verified'] = False
        with self.assertRaises(RuntimeError):
            self.select('f' * 64)

    def test_retired_build_cannot_be_reactivated_by_a_profile(self):
        self.free['version'] = '21.1.0.14'
        with self.assertRaises(RuntimeError):
            self.select('f' * 64, '21.1.0.14')

    def test_missing_hash_cannot_authorize_writes(self):
        self.free.pop('executable_sha256')
        with self.assertRaises(RuntimeError):
            self.select('f' * 64)

    def test_duplicate_matches_are_rejected(self):
        self.profiles['duplicate'] = copy.deepcopy(self.studio)
        with self.assertRaisesRegex(RuntimeError, 'Ambiguous'):
            self.select(self.studio['executable_sha256'])

    def test_connection_selects_free_before_requesting_process_access(self):
        import resolve_palette
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = root / 'Resolve.exe'
            executable.write_bytes(b'free edition fixture')
            self.free['executable_sha256'] = hashlib.sha256(executable.read_bytes()).hexdigest()
            (root / 'compatibility_profiles.json').write_text(json.dumps(self.profiles))
            api = Mock()
            api.OpenProcess.return_value = 0
            with patch.object(resolve_palette, 'kernel', return_value=api), \
                    patch.object(resolve_palette, 'discover', return_value=(123, 4096, str(executable))), \
                    patch.object(resolve_palette, 'file_version', return_value='21.1.1.10'):
                session = resolve_palette.PaletteSession(root)
                with self.assertRaisesRegex(RuntimeError, 'Windows denied access'):
                    session.connect()
                self.assertEqual(session.signature['edition'], 'free')
                api.OpenProcess.assert_called_once()

    def test_unknown_executable_never_requests_writable_process_access(self):
        import resolve_palette
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = root / 'Resolve.exe'
            executable.write_bytes(b'unrecognized executable')
            (root / 'compatibility_profiles.json').write_text(json.dumps(self.profiles))
            api = Mock()
            with patch.object(resolve_palette, 'kernel', return_value=api), \
                    patch.object(resolve_palette, 'discover', return_value=(123, 4096, str(executable))), \
                    patch.object(resolve_palette, 'file_version', return_value='21.1.1.10'):
                session = resolve_palette.PaletteSession(root)
                with self.assertRaisesRegex(RuntimeError, 'No verified'):
                    session.connect()
                api.OpenProcess.assert_not_called()


if __name__ == '__main__':
    unittest.main()
