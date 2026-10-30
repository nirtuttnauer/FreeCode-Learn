import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit_public_bundle',ROOT/'scripts/audit_public_bundle.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class PublicReleaseTests(unittest.TestCase):
    def test_public_data_is_exactly_the_original_course_inventory(self):
        result=audit.audit(ROOT/'data')
        self.assertEqual(result['profile'],'public')
        self.assertEqual(result['importedProblems'],0)
        self.assertEqual(result['importedPlaylists'],0)
        self.assertEqual(result['originalLearningSteps'],231)

    def test_imported_data_and_unexpected_files_fail_the_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'data';shutil.copytree(ROOT/'data',root)
            (root/'problems').mkdir()
            with self.assertRaises(AssertionError):audit.audit(root)
            (root/'problems').rmdir();(root/'progress.json').write_text('{}')
            with self.assertRaises(AssertionError):audit.audit(root)


if __name__=='__main__':unittest.main()
