import importlib.util
import io
from pathlib import Path
import platform
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


packaging = load('prepare_runtimes', 'scripts/prepare_runtimes.py')
runner = load('bundled_runner', 'scripts/runner.py')


class RuntimePackagingTests(unittest.TestCase):
    def test_bundle_wins_over_host_and_missing_bundle_never_uses_host(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(runner, 'ROOT', Path(temp)):
            executable = Path(temp) / 'runtimes' / platform.machine() / 'node/bin/node'
            executable.parent.mkdir(parents=True)
            executable.write_text('#!/bin/sh\nexit 0\n')
            executable.chmod(0o755)
            with patch.object(runner.shutil, 'which', side_effect=AssertionError('host lookup')):
                self.assertEqual(runner.tool('node'), str(executable))
                executable.unlink()
                with self.assertRaisesRegex(RuntimeError, 'Bundled node is missing'):
                    runner.tool('node')
            with patch.object(runner, 'ROOT', Path(temp) / 'PracticeCode.app/Contents/Resources'):
                with self.assertRaisesRegex(RuntimeError, 'Bundled java is missing'):
                    runner.tool('java')

    def test_rejects_traversal_and_writes_through_symlinks(self):
        for entries in [[('../escape', None)], [('root/link', '../outside'), ('root/link/file', None)]]:
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as temp:
                archive = Path(temp) / 'bad.tar'
                with tarfile.open(archive, 'w') as target:
                    for name, link in entries:
                        member = tarfile.TarInfo(name)
                        if link:
                            member.type, member.linkname = tarfile.SYMTYPE, link
                            target.addfile(member)
                        else:
                            member.size = 1
                            target.addfile(member, io.BytesIO(b'x'))
                with self.assertRaises(ValueError):
                    packaging.validate_archive(archive)

    def test_accepts_internal_executable_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / 'valid.tar'
            with tarfile.open(archive, 'w') as target:
                binary = tarfile.TarInfo('python/bin/python3.12')
                binary.size = 1
                target.addfile(binary, io.BytesIO(b'x'))
                link = tarfile.TarInfo('python/bin/python3')
                link.type, link.linkname = tarfile.SYMTYPE, 'python3.12'
                target.addfile(link)
            packaging.validate_archive(archive)
