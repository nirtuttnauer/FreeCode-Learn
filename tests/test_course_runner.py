import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import course_support

import platform
PYTHON=ROOT/('.cache/runtime-bundle/'+platform.machine()+'/python/bin/python3')
if not PYTHON.exists():PYTHON=Path(sys.executable)


def run_step(step,files,action='check',environment=None):
    request=dict(mode='course',courseStep=str(step['id']),courseFiles=json.dumps(files),courseAction=action)
    process=subprocess.run([str(PYTHON),'-I','-B',str(ROOT/'scripts/runner.py')],input=json.dumps(request),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment,timeout=135)
    if process.returncode:raise AssertionError(process.stderr or process.stdout)
    return json.loads(process.stdout)


class CourseRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'data/learning/python-engineer/manifest.json').read_text())
        cls.step=next(iter(cls.manifest['steps'].values()))
        cls.workspace=cls.manifest['workspaces'][cls.step['workspaceID']]

    def test_reference_passes_starter_fails_and_environment_cannot_select_solution(self):
        files=dict(self.workspace['files']);files[self.workspace['entrypoint']]=self.workspace['reference']
        passed=run_step(self.step,files)
        self.assertTrue(passed['success'],passed.get('output'))
        self.assertTrue(passed['cases'])
        self.assertEqual(passed['course']['fingerprint'],course_support.fingerprint(files))
        failed=run_step(self.step,self.workspace['files'],environment=dict(os.environ,SOLUTIONS='1'))
        self.assertFalse(failed['success'])

    def test_demo_and_learner_checks_are_never_graded(self):
        result=run_step(self.step,self.workspace['files'],'demo')
        self.assertTrue(result['success'],result.get('output'))
        self.assertFalse(result['course']['graded'])
        files=dict(self.workspace['files']);files['test_learner.py']='def test_local():\n    assert 2+2==4\n'
        result=run_step(self.step,files,'learner')
        self.assertTrue(result['success'],result.get('output'))
        self.assertFalse(result['course']['graded'])

    def test_unsafe_paths_and_collisions_are_rejected(self):
        for name in ['../a.py','/tmp/a.py','src/../a.py','.hidden/a.py','src\\a.py','checks/a.py']:
            with self.subTest(name=name),self.assertRaises(ValueError):course_support.validate_files({name:''})
        with self.assertRaises(ValueError):course_support.validate_files({'a.py':'','a.py/b.py':''})

    def test_backend_shares_files_invalidates_siblings_and_backs_up_reset(self):
        sys.path.insert(0,str(ROOT/'app/linux'))
        spec=importlib.util.spec_from_file_location('course_backend',ROOT/'app/linux/backend.py')
        backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
        with tempfile.TemporaryDirectory() as directory:
            store=backend.Store(ROOT,directory)
            siblings=[s for s in self.manifest['steps'].values() if s['workspaceID']==self.step['workspaceID']]
            files=dict(self.workspace['files']);files[self.workspace['entrypoint']]=self.workspace['reference']
            store.save(self.step['id'],'python',{'files':files})
            prepared=store.prepare_run(self.step['id'],'python')
            result=run_step(self.step,files)
            store.complete_run(prepared['token'],result)
            self.assertEqual(store.progress()[str(self.step['id'])]['status'],'Solved')
            store.save(siblings[1]['id'],'python',{'code':files[self.workspace['entrypoint']]+'\n# changed\n'})
            self.assertEqual(store.progress()[str(self.step['id'])]['status'],'In progress')
            shared=store.workspace(self.step['id'],'python')
            self.assertIn('# changed',shared['code'])
            before=shared['files']
            backup=Path(store.reset()['backup'])
            self.assertTrue(list(backup.glob('course-*.json')))
            self.assertNotEqual(store.workspace(self.step['id'],'python')['files'],before)

    def test_stale_result_and_skips_do_not_complete(self):
        import importlib
        sys.path.insert(0,str(ROOT/'app/linux'));backend=importlib.import_module('backend')
        with tempfile.TemporaryDirectory() as directory:
            store=backend.Store(ROOT,directory)
            files=dict(self.workspace['files']);files[self.workspace['entrypoint']]=self.workspace['reference']
            store.save(self.step['id'],'python',{'files':files})
            prepared=store.prepare_run(self.step['id'],'python')
            result=run_step(self.step,files)
            store.save(self.step['id'],'python',{'code':files[self.workspace['entrypoint']]+'\n# stale\n'})
            store.complete_run(prepared['token'],result)
            self.assertNotEqual(store.progress()[str(self.step['id'])]['status'],'Solved')


if __name__=='__main__':unittest.main()
