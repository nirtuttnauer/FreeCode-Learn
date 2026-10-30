import importlib.util
import plistlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'scripts/install_app.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'build/FreeCode.app'
        self.destination = self.root / 'Applications/FreeCode.app'
        for bundle, version in [(self.source, 'new'), (self.destination, 'old')]:
            (bundle / 'Contents').mkdir(parents=True)
            (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': installer.IDENTIFIER}))
            (bundle / 'Contents/version').write_text(version)
        (self.destination / 'stale-resource').write_text('remove on replacement')

    def commands(self, args, **kwargs):
        if args[0] == 'ditto':
            shutil.copytree(args[1], args[2])
        elif args[0] not in {'codesign', 'open'} and not args[0].endswith('/lsregister'):
            self.fail(f'Unexpected installer command: {args}')
        return subprocess.CompletedProcess(args, 0)

    def test_replaces_complete_bundle_and_reopens_installed_copy(self):
        with patch.object(installer.subprocess, 'run', side_effect=self.commands) as commands, \
             patch.object(installer, 'is_running', return_value=True), \
             patch.object(installer, 'quit_running_app') as quit_app:
            installer.install_app(self.source, self.destination)
        quit_app.assert_called_once()
        self.assertEqual((self.destination / 'Contents/version').read_text(), 'new')
        self.assertFalse((self.destination / 'stale-resource').exists())
        self.assertEqual(list(self.destination.parent.glob('.FreeCode-*')), [])
        self.assertIn(unittest.mock.call(['open', str(self.destination)], check=True), commands.call_args_list)

    def test_copy_and_replacement_failures_preserve_installed_app(self):
        rename = Path.rename

        def reject_staged_rename(path, destination):
            if path.parent.name.startswith('.FreeCode-update-'):
                raise OSError('simulated replacement failure')
            return rename(path, destination)

        for phase in ['copy', 'replace']:
            with self.subTest(phase=phase):
                def command(args, **kwargs):
                    if phase == 'copy' and args[0] == 'ditto':
                        raise subprocess.CalledProcessError(1, args)
                    return self.commands(args, **kwargs)

                with patch.object(installer.subprocess, 'run', side_effect=command), \
                     patch.object(installer, 'is_running', return_value=False), \
                     patch.object(Path, 'rename', reject_staged_rename), \
                     self.assertRaises((OSError, subprocess.CalledProcessError)):
                    installer.install_app(self.source, self.destination)
                self.assertEqual((self.destination / 'Contents/version').read_text(), 'old')
                self.assertTrue((self.destination / 'stale-resource').exists())
                self.assertEqual(list(self.destination.parent.glob('.FreeCode-*')), [])

    def test_refuses_to_overwrite_a_different_application(self):
        (self.destination / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': 'unrelated.app'}))
        with patch.object(installer.subprocess, 'run', side_effect=self.commands), \
             self.assertRaisesRegex(RuntimeError, 'different application'):
            installer.install_app(self.source, self.destination)
        self.assertEqual((self.destination / 'Contents/version').read_text(), 'old')


if __name__ == '__main__':
    unittest.main()
