import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


class CourseContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'data/learning/python-engineer/manifest.json').read_text())

    def test_all_modules_projects_and_steps_have_stable_ids_and_checks(self):
        workspaces=self.manifest['workspaces']
        self.assertEqual(sum(w['kind']=='module' for w in workspaces.values()),26)
        self.assertEqual(sum(w['kind']=='project' for w in workspaces.values()),5)
        steps=self.manifest['steps']
        ids=json.loads((ROOT/'courses/python-engineer/ids.json').read_text())
        self.assertEqual(set(ids.values()),{int(k) for k in steps})
        self.assertEqual(len(steps),203)
        self.assertTrue(any(w.get('module')=='13' for w in workspaces.values()))
        for identifier,step in steps.items():
            with self.subTest(step=step['checkGroup']):
                w=workspaces[step['workspaceID']]
                self.assertLess(int(identifier),-3000)
                self.assertTrue(step['selectors'])
                for selector in step['selectors']:
                    name,*nodes=selector.split('::')
                    self.assertIn(name,w['tests'])
                    for node in nodes:self.assertRegex(w['tests'][name],r'(?:class|def) '+re.escape(node)+r'\b')
                p=json.loads((ROOT/'data/learning/problems'/f'{identifier}.json').read_text())
                self.assertEqual(p['course']['version'],step['version'])
                self.assertIn('Hint',p['statement'])
                self.assertNotIn('src="https://',p['statement'])

    def test_catalog_and_groups_match_exactly(self):
        course=next(c for c in json.loads((ROOT/'data/learning/courses.json').read_text()) if c['id']=='python-engineer')
        self.assertEqual(course['name'],'Python Engineer')
        self.assertEqual(len(course['groups']),31)
        self.assertEqual({i for g in course['groups'] for i in g['questionIDs']},{int(k) for k in self.manifest['steps']})
        self.assertTrue(all(len([s for s in self.manifest['steps'].values() if s['workspaceID']==wid])==6 for wid,w in self.manifest['workspaces'].items() if w['kind']=='project'))

    def test_additional_course_compiles_without_touching_the_existing_library(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'course/source/01_basics';source.mkdir(parents=True)
            (root/'course/course.json').write_text(json.dumps(dict(id='example-course',name='Example Course')))
            (source/'README.md').write_text('# Basics\nLearn to double a number.\n')
            (source/'exercises_01.py').write_text('def double(value):\n    """Return twice the value."""\n    raise NotImplementedError\n')
            (source/'solutions_01.py').write_text('def double(value):\n    return value*2\n')
            (source/'test_01.py').write_text('from courselib import impl\nm=impl("01")\ndef test_double():\n    assert m.double(2)==4\n')
            subprocess.run([sys.executable,'-B',str(ROOT/'scripts/build_python_engineer.py'),'--course',str(root/'course'),'--output',str(root/'learning')],check=True,stdout=subprocess.PIPE)
            manifest=json.loads((root/'learning/example-course/manifest.json').read_text())
            step=next(iter(manifest['steps'].values()))
            self.assertEqual(step['courseID'],'example-course')
            self.assertEqual(step['workspaceID'],'example-course-01')

    def test_public_staging_uses_original_content_only(self):
        spec=importlib.util.spec_from_file_location('stage_content',ROOT/'scripts/stage_content.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'data';mod.stage(target,'public')
            self.assertEqual(json.loads((target/'catalog.json').read_text()),[])
            self.assertFalse((target/'problems').exists())
            self.assertFalse((target/'DOOCS-LICENSE.txt').exists())
            self.assertFalse(any('official-' in p.name for p in target.rglob('*')))
            lessons=json.loads((target/'learning/catalog.json').read_text())
            self.assertTrue(all(p['id']<0 for p in lessons))
            self.assertEqual(len(lessons),len(json.loads((ROOT/'data/learning/catalog.json').read_text())))


if __name__=='__main__':unittest.main()
