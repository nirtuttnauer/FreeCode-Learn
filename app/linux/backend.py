#!/usr/bin/env python3
"""Local JSON-lines state service. No sockets, remote service, or shell commands."""
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
try:
    import course_support
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bundle/scripts"))
    import course_support

LANGUAGES = {'python', 'javascript', 'cpp', 'java', 'sql'}
PROGRAMS = {
    'python': 'import sys\n\ndef main():\n    data = sys.stdin.read()\n    print(data.strip())\n\nif __name__ == "__main__":\n    main()\n',
    'javascript': 'const fs = require("fs");\nconst input = fs.readFileSync(0, "utf8");\nconsole.log(input.trim());\n',
    'cpp': '#include <iostream>\n#include <string>\nusing namespace std;\nint main() { string s; while (getline(cin, s)) cout << s << "\\n"; }\n',
    'java': 'import java.util.*;\npublic class Main { public static void main(String[] args) { Scanner in = new Scanner(System.in); while(in.hasNextLine()) System.out.println(in.nextLine()); } }\n',
    'sql': '-- Write your SQLite query here.\n',
}


def read_json(path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return copy.deepcopy(default)
    except (OSError, ValueError) as exc:
        raise ValueError(f'Could not read {path.name}. The original file is preserved: {exc}')


def atomic(path, value):
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def draft_value(field):
    kind, text = field['kind'], field['text']
    if kind == 'Text':
        return text
    if kind == 'Null':
        return None
    value = json.loads(text)
    valid = (kind == 'Number' and type(value) in (int, float) and math.isfinite(value)
             or kind == 'Boolean' and type(value) is bool
             or kind == 'Array' and isinstance(value, list)
             or kind == 'Object' and isinstance(value, dict))
    if not valid:
        raise ValueError('Choose the matching type and enter a valid value.')
    return value


def tests_from_workspace(workspace):
    if workspace.get('testCaseDrafts') is not None:
        tests = [dict(args=[draft_value(v) for v in case['arguments']], expected=draft_value(case['expected']), unordered=bool(case.get('unordered')))
                 for case in workspace['testCaseDrafts']]
    else:
        tests = json.loads(workspace['tests'])
    if not isinstance(tests, list) or not 1 <= len(tests) <= 50:
        raise ValueError('Provide 1–50 test cases.')
    for case in tests:
        if not isinstance(case, dict) or not isinstance(case.get('args'), list) or 'expected' not in case:
            raise ValueError('Each test needs inputs and an expected value.')
    json.dumps(tests, allow_nan=False)
    return tests


class Store:
    def __init__(self, bundle, work):
        self.bundle, self.work = Path(bundle), Path(work)
        self.work.mkdir(parents=True, exist_ok=True)
        self.catalog = read_json(self.bundle / 'data/catalog.json', [])
        self.lessons = read_json(self.bundle / 'data/learning/catalog.json', [])
        self.known = {p['id']: p for p in self.catalog + self.lessons}
        self.plans = read_json(self.bundle / 'data/playlists.json', [])
        self.courses = read_json(self.bundle / 'data/learning/courses.json', [])
        self.course_steps = course_support.all_steps(self.bundle / 'data/learning')
        self.pending = {}
        self.progress(); self.lists(); self.settings(); self.activity()

    def progress(self):
        value = read_json(self.work / 'progress.json', {})
        if not isinstance(value, dict):
            raise ValueError('Progress file is invalid; it has been preserved.')
        for identifier, step in self.course_steps.items():
            record = value.get(identifier, {})
            if record.get('status') == 'Solved' and record.get('courseVersion') != step['version']:
                record['status'] = 'In progress'
        return value

    def activity(self):
        value = read_json(self.work / 'activity.json', [])
        if not isinstance(value, list):
            raise ValueError('Activity file is invalid; it has been preserved.')
        return value

    def lists(self):
        value = read_json(self.work / 'custom-lists.json', [])
        if not isinstance(value, list) or any(not isinstance(x, dict) or not isinstance(x.get('questionIDs'), list) or not isinstance(x.get('name'), str) or not isinstance(x.get('id'), str) for x in value):
            raise ValueError('Custom lists file is invalid; it has been preserved.')
        return value

    def settings(self):
        value = read_json(self.work / 'settings.json', {'appearanceMode': 'system'})
        if not isinstance(value, dict):
            raise ValueError('Settings file is invalid; it has been preserved.')
        return value

    def key(self, problem_id, language):
        if type(problem_id) is not int or problem_id not in self.known or language not in LANGUAGES:
            raise ValueError('Unknown question or language.')
        if problem_id < 0 and language != 'python':
            raise ValueError('Learning lessons use Python.')
        course = self.problem(problem_id).get("course")
        return f'course-{course["workspaceID"]}-python' if course else f'{problem_id}-{language}'

    def problem(self, problem_id):
        if type(problem_id) is not int or problem_id not in self.known:
            raise ValueError('Unknown question.')
        folder = 'learning/problems' if problem_id < 0 else 'problems'
        return read_json(self.bundle / f'data/{folder}/{problem_id}.json', None)

    def workspace(self, problem_id, language):
        key = self.key(problem_id, language)
        problem = self.problem(problem_id)
        samples = [dict(args=s['args'], expected=s['expected']) for s in problem['samples'] if s.get('args') is not None and 'expected' in s]
        starter = problem['starters'].get(language)
        default = dict(code=starter if starter is not None else PROGRAMS[language], tests=json.dumps(samples),
                       stdin=problem.get('sqlSetup', '') if language == 'sql' else '', mode='sql' if language == 'sql' else 'function' if starter is not None else 'program')
        if problem.get('course'):
            course = problem['course']
            files = read_json(self.bundle / ('data/learning/' + course.get('courseID','python-engineer') + '/' + course['workspaceID'] + '.json'), None)
            default.update(files=files, selectedFile=course['entrypoint'], mode='course', code=files[course['entrypoint']])
        value = read_json(self.work / (key + '.json'), default)
        if problem.get('course'):
            course_support.validate_files(value.get('files'))
            if value.get('selectedFile') not in value['files']:
                raise ValueError('Saved course file selection is invalid; the workspace is preserved.')
        if not isinstance(value, dict) or any(not isinstance(value.get(k), str) for k in ['code', 'tests', 'stdin', 'mode']):
            raise ValueError('Saved workspace is invalid; the file is preserved.')
        if problem_id <= -2001 and 'System design' in problem['tags'] and value.get('design') is None:
            value['design'] = design.workspace()
        return value

    def account(self):
        return dict(progress=self.progress(), activity=self.activity(), lists=self.lists(), settings=self.settings())

    def bootstrap(self, **_):
        return dict(catalog=self.catalog, lessons=self.lessons, playlists=self.plans, courses=self.courses,
                    courseSteps=self.course_steps, coverage=read_json(self.bundle / 'data/coverage.json', {}), programs=PROGRAMS, workDirectory=str(self.work), **self.account())

    def open(self, id, language):
        value = self.workspace(id, language)
        problem=self.problem(id)
        course=problem.get('course')
        starters=read_json(self.bundle / ('data/learning/' + course.get('courseID','python-engineer') + '/' + course['workspaceID'] + '.json'), {}) if course else None
        return dict(problem=problem, workspace=value, testError=self.test_error(value), starterFiles=starters)

    @staticmethod
    def test_error(workspace):
        if workspace['mode'] != 'function':
            return None
        try:
            tests_from_workspace(workspace)
        except (ValueError, KeyError, TypeError) as exc:
            return str(exc)
        return None

    def save(self, id, language, patch):
        allowed = {'code', 'tests', 'stdin', 'mode', 'testCaseDrafts', 'design', 'notes', 'favorite', 'files', 'selectedFile'}
        if not isinstance(patch, dict) or not set(patch) <= allowed:
            raise ValueError('Unsupported edit. Progress is automatic and cannot be set manually.')
        key = self.key(id, language); value = self.workspace(id, language)
        for field in ['code', 'tests', 'stdin', 'notes']:
            if field in patch and (not isinstance(patch[field], str) or len(patch[field]) > 1_000_000):
                raise ValueError('Text fields must be at most 1 MB.')
        if 'mode' in patch and patch['mode'] not in {'function', 'program', 'sql', 'course'}:
            raise ValueError('Unknown execution mode.')
        if 'testCaseDrafts' in patch and (not isinstance(patch['testCaseDrafts'], list) or len(patch['testCaseDrafts']) > 50):
            raise ValueError('Use at most 50 test drafts.')
        if 'design' in patch and (id > -2001 or not isinstance(patch['design'], dict) or len(json.dumps(patch['design'])) > 5_000_000):
            raise ValueError('Design drafts belong to system-design lessons and must be under 5 MB.')
        if 'favorite' in patch and type(patch['favorite']) is not bool:
            raise ValueError('Favorite must be a boolean.')
        course = self.problem(id).get('course')
        if course:
            if 'mode' in patch and patch['mode'] != 'course':
                raise ValueError('Course steps use required course checks.')
            new_files = patch.get('files', value['files'])
            course_support.validate_files(new_files)
            selected = patch.get('selectedFile', value['selectedFile'])
            if selected not in new_files or course['entrypoint'] not in new_files:
                raise ValueError('Keep the required entry file and select an existing file.')
            if 'code' in patch:
                new_files = dict(new_files); new_files[selected] = patch['code']
            patch = dict(patch, files=new_files, selectedFile=selected, code=new_files[selected])
        elif any(k in patch for k in ['files','selectedFile']):
            raise ValueError('Files belong to a course workspace.')
        progress = self.progress(); record = progress.setdefault(str(id), dict(status='Unstarted', favorite=False, notes=''))
        changed_solution = any(k in patch and value.get(k) != patch[k] for k in ['code', 'tests', 'stdin', 'mode', 'testCaseDrafts', 'files'])
        if course:
            changed_solution = value.get('files') != patch.get('files')
            if changed_solution:
                for step_id, step in self.course_steps.items():
                    if step['workspaceID'] == course['workspaceID'] and step_id in progress:
                        progress[step_id]['status'] = 'In progress'
        if changed_solution or ('design'  in patch and record['status'] == 'Unstarted'):
            record['status'] = 'In progress'
        for field in ['notes', 'favorite']:
            if field in patch:
                record[field] = patch[field]
        value.update({k: v for k, v in patch.items() if k not in {'notes', 'favorite'}})
        error = self.test_error(value)
        if not error and value['mode'] == 'function':
            value['tests'] = json.dumps(tests_from_workspace(value), ensure_ascii=False)
        atomic(self.work / (key + '.json'), value)
        atomic(self.work / 'progress.json', progress)
        return dict(record=record, testError=error)

    def set_settings(self, appearanceMode):
        if appearanceMode not in {'system', 'light', 'dark'}:
            raise ValueError('Choose System, Light, or Dark.')
        value = self.settings(); value['appearanceMode'] = appearanceMode
        atomic(self.work / 'settings.json', value)
        return value

    def edit_list(self, action, name='', listID=None, questionID=None):
        lists = self.lists()
        if action in {'create', 'rename'}:
            name = name.strip()
            if not name or len(name) > 80 or any(x['name'].casefold() == name.casefold() and x['id'] != listID for x in lists):
                raise ValueError('Choose a unique list name with 1–80 characters.')
        if action == 'create':
            lists.append(dict(id='custom-' + str(uuid.uuid4()), name=name, questionIDs=[]))
        else:
            target = next((x for x in lists if x['id'] == listID), None)
            if target is None:
                raise ValueError('List no longer exists.')
            if action == 'rename':
                target['name'] = name
            elif action == 'delete':
                lists.remove(target)
            elif action == 'toggle':
                if type(questionID) is not int or questionID not in {p['id'] for p in self.catalog}:
                    raise ValueError('Only library questions can be added to personal lists.')
                if questionID in target['questionIDs']:
                    target['questionIDs'].remove(questionID)
                else:
                    target['questionIDs'].append(questionID)
            else:
                raise ValueError('Unknown list action.')
        atomic(self.work / 'custom-lists.json', lists)
        return lists

    @staticmethod
    def fingerprint(value):
        return hashlib.sha256(json.dumps({k: value.get(k) for k in ['code', 'tests', 'stdin', 'mode', 'testCaseDrafts']}, sort_keys=True).encode()).hexdigest()

    def prepare_run(self, id, language, action="check"):
        if self.pending:
            raise ValueError('Stop the current run before starting another.')
        self.key(id, language); value = self.workspace(id, language)
        error = self.test_error(value)
        if error:
            raise ValueError(error)
        token = str(uuid.uuid4())
        request = {k: value[k] for k in ['code', 'tests', 'stdin', 'mode']}
        request.update(language=language, reference=self.problem(id)['references'].get(language, value['code']))
        if self.problem(id).get('course'):
            request.update(mode='course', courseStep=str(id), courseFiles=json.dumps(value['files']), courseAction=action)
        self.pending[token] = dict(action=action, id=id, language=language, fingerprint=self.fingerprint(value), mode=value['mode'], count=len(tests_from_workspace(value)) if value['mode'] == 'function' else 0)
        progress = self.progress()
        if action == 'check': progress.setdefault(str(id), dict(favorite=False, notes=''))['status'] = 'In progress'
        atomic(self.work / 'progress.json', progress)
        return dict(token=token, request=request)

    def complete_run(self, token, result):
        run = self.pending.pop(token)
        progress = self.progress(); value = self.workspace(run['id'], run['language'])
        cases = result.get('cases') or []
        if self.fingerprint(value) == run['fingerprint'] and not self.test_error(value):
            solved = run['mode'] == 'function' and run['language'] != 'sql' and result.get('success') is True and run['count'] > 0 and len(cases) == run['count'] and all(c.get('passed') is True for c in cases)
            if run['mode'] == 'course':
                step = self.course_steps[str(run['id'])]
                proof = result.get('course') or {}
                solved = result.get('success') is True and bool(cases) and all(c.get('passed') is True for c in cases) and proof.get('graded') is True and all(proof.get(k) == step[k] for k in ['workspaceID','checkGroup','version']) and proof.get('fingerprint') == course_support.fingerprint(value['files'])
            if run['action'] == 'check':
                progress.setdefault(str(run['id']), dict(favorite=False, notes=''))['status'] = 'Solved' if solved else 'In progress'
                if run['mode'] == 'course': progress[str(run['id'])]['courseVersion'] = step['version']
            atomic(self.work / 'progress.json', progress)
        activity = self.activity()
        activity.append(dict(id=str(uuid.uuid4()), problemID=run['id'], language=run['language'], mode=run['mode'], success=bool(result.get('success')), passed=sum(c.get('passed') is True for c in cases), total=len(cases), duration=result.get('duration'), stopped=bool(result.get('stopped')), date=datetime.now().astimezone().isoformat()))
        atomic(self.work / 'activity.json', activity)
        return dict(result=result, **self.account())

    def experiment(self, id, language):
        value = self.workspace(id, language); draft = value.get('design')
        if not draft:
            raise ValueError('Open a system-design lesson first.')
        result = design.simulate(draft['diagram'], draft['scenario'])
        if not result['valid']:
            raise ValueError(result['observations'][0])
        draft.setdefault('experiments', []).append(dict(id=str(uuid.uuid4()), date=datetime.now().astimezone().isoformat(), name=f"Experiment {len(draft.get('experiments', [])) + 1}", diagram=copy.deepcopy(draft['diagram']), scenario=copy.deepcopy(draft['scenario']), result=result))
        self.save(id, language, {'design': draft})
        return dict(design=draft, result=result)

    def simulate(self, diagram, scenario):
        return design.simulate(diagram, scenario)

    def reset(self):
        if self.pending:
            raise ValueError('Stop the current run before resetting.')
        files = [p for p in self.work.glob('*.json') if p.name in {'progress.json', 'activity.json', 'custom-lists.json'} or re.fullmatch(r'(?:-?\d+-(?:python|javascript|cpp|java|sql)|course-python-engineer-[a-z0-9-]+-python)\.json', p.name)]
        backup = self.work / 'backups' / (datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ-') + uuid.uuid4().hex[:8])
        backup.mkdir(parents=True)
        removed = []
        try:
            for path in files:
                shutil.copy2(path, backup / path.name)
                if path.read_bytes() != (backup / path.name).read_bytes():
                    raise OSError('Recovery backup did not match the original.')
            for path in files:
                path.unlink(); removed.append(path)
        except OSError:
            for path in removed:
                shutil.copy2(backup / path.name, path)
            raise
        return dict(backup=str(backup), **self.account())


def main():
    store = Store(os.environ['FREECODE_BUNDLE_ROOT'], os.environ['OFFLINE_PRACTICE_WORK_DIR'])
    allowed = {k: getattr(store, k) for k in ['bootstrap', 'open', 'save', 'set_settings', 'edit_list', 'prepare_run', 'complete_run', 'experiment', 'simulate', 'reset']}
    for line in sys.stdin:
        request = {}
        try:
            if len(line) > 8_000_000:
                raise ValueError('Request exceeds 8 MB.')
            request = json.loads(line)
            if request['method'] not in allowed:
                raise ValueError('Unknown operation.')
            response = dict(id=request['id'], result=allowed[request['method']](**request.get('params', {})))
        except Exception as exc:
            response = dict(id=request.get('id'), error=str(exc))
        print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
