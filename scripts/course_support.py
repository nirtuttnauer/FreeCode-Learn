"""Shared course validation and offline execution. No app-specific state."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
import time
import xml.etree.ElementTree as ET


def validate_files(files):
    if not isinstance(files, dict) or not 1 <= len(files) <= 200:
        raise ValueError('A course workspace needs 1–200 text files.')
    total = 0
    for name, content in files.items():
        if not isinstance(name, str): raise ValueError('File names must be text.')
        path = PurePosixPath(name)
        if not isinstance(name, str) or not name or '\\' in name or path.is_absolute() or any(p in {'..', '.', ''} or p.startswith('.') for p in name.split('/')):
            raise ValueError('Use relative file names without hidden directories or parent paths.')
        if len(name) > 240 or path.suffix not in {'.py', '.md', '.toml', '.json', '.txt', '.html', '.sql', '.yaml', '.yml', '.css', '.svg'}:
            raise ValueError('Use a supported source, documentation, template, or data file.')
        if not isinstance(content, str) or len(content.encode()) > 1_000_000:
            raise ValueError('Each course file must be text under 1 MB.')
        total += len(content.encode())
        if name.startswith(('checks/', 'trusted/', 'course-internal/')):
            raise ValueError('That directory belongs to the required checks.')
    if total > 5_000_000:
        raise ValueError('Course files exceed 5 MB.')
    if any(str(p) != name and str(p) in files for name in files for p in PurePosixPath(name).parents):
        raise ValueError('A file cannot also be a directory.')
    return files


def fingerprint(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


def metadata(learning, identifier):
    for path in sorted(Path(learning).glob('*/manifest.json')):
        manifest = json.loads(path.read_text())
        step = manifest['steps'].get(str(identifier))
        if step is not None: return step, manifest['workspaces'][step['workspaceID']]
    raise ValueError('This course step is not installed.')


def all_steps(learning):
    steps = {}
    for path in sorted(Path(learning).glob('*/manifest.json')):
        manifest = json.loads(path.read_text())
        if steps.keys() & manifest['steps'].keys(): raise ValueError('Duplicate course step IDs.')
        steps.update(manifest['steps'])
    return steps


def run(request, execute, learning):
    started = time.monotonic()
    step, workspace = metadata(learning, request['courseStep'])
    files = validate_files(json.loads(request['courseFiles']))
    action = request.get('courseAction', 'check')
    if action not in {'check', 'demo', 'learner', 'lint', 'typecheck', 'benchmark'}:
        raise ValueError('Unknown course action.')
    if workspace['entrypoint'] not in files:
        raise ValueError('Restore or create the required entry file: ' + workspace['entrypoint'])
    with tempfile.TemporaryDirectory(prefix='practicecode-course-') as temp:
        root = Path(temp)
        submission = root / 'submission'
        submission.mkdir()
        for name, content in files.items():
            target = submission / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        trusted = root / 'trusted'
        trusted.mkdir()
        (root/'pyproject.toml').write_text('[project]\nname = "python-engineer"\nversion = "0.1.0"\ndependencies = []\n[project.optional-dependencies]\ndev = ["pytest>=8.0", "hypothesis>=6.100"]\n')
        (root/'courselib.py').write_text('# Python Engineer course fixture; the execution loader is in trusted/.\n')
        for name, content in workspace['tests'].items():
            target = trusted / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        if workspace['kind'] == 'module':
            # This loader never accepts SOLUTIONS from the parent environment.
            (trusted/'courselib.py').write_text('import importlib\ndef impl(number):\n    return importlib.import_module("exercises_" + number)\n')
        payload = dict(submission=str(submission), trusted=str(trusted), action=action,
                       selectors=step['selectors'], kind=workspace['kind'], module=workspace.get('module'),
                       demo=workspace['demo'], report=str(root/'report.xml'), result=str(root/'worker-result.json'))
        path = root / 'request.json'
        path.write_text(json.dumps(payload))
        output = execute([sys.executable, '-I', '-B', str(Path(__file__).with_name('course_worker.py')), str(path)], root, timeout=120)
        result = json.loads((root/'worker-result.json').read_text())
        cases = result.get('cases', [])
        success = result.get('exitCode') == 0 and (action != 'check' or bool(cases) and all(c['passed'] for c in cases))
        return dict(success=success, message=(f"{sum(c['passed'] for c in cases)}/{len(cases)} required checks passed" if action=='check' else action.title() + (' finished' if success else ' needs attention')),
                    output=(result.get('output','') + '\n' + output).strip()[-60000:], cases=cases, duration=time.monotonic()-started,
                    course=dict(workspaceID=workspace['id'], checkGroup=step['checkGroup'], version=step['version'], fingerprint=fingerprint(files), graded=action=='check', action=action))
