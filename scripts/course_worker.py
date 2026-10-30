#!/usr/bin/env python3
"""Runs only in a disposable course submission directory under the bundled Python."""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import traceback
import xml.etree.ElementTree as ET


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    packages = Path(__file__).resolve().parent.parent / 'course-packages'
    # .pth files are deliberately not executed; wheel contents are imported directly.
    arch = 'arm64' if __import__('platform').machine() in {'arm64','aarch64'} else 'x86_64'
    if not (packages / arch).exists():
        packages = Path(__file__).resolve().parent.parent / '.cache/course-packages'
        arch = ('macos-' if sys.platform == 'darwin' else 'linux-') + arch
    if (packages / arch).exists(): sys.path.insert(0,str(packages / arch))
    submission, trusted = Path(request['submission']), Path(request['trusted'])
    os.chdir(submission)
    sys.path[:0] = [str(trusted), str(submission/'src'), str(submission)]
    os.environ.pop('SOLUTIONS', None)
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    os.environ['HYPOTHESIS_STORAGE_DIRECTORY'] = str(submission.parent/'hypothesis')
    os.environ.pop('OTEL_SDK_DISABLED', None)
    os.environ['OTEL_TRACES_EXPORTER'] = 'none'
    os.environ['OTEL_METRICS_EXPORTER'] = 'none'
    os.environ['OTEL_LOGS_EXPORTER'] = 'none'
    output = io.StringIO()
    code, cases = 0, []
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            action = request['action']
            if action == 'demo':
                if not request['demo']: raise ValueError('This project has no demonstration. Use the specification and milestone checks.')
                exec(compile(request['demo'], '<course-demonstration>', 'exec'), {'__name__':'__main__'})
            elif action == 'lint':
                from ruff import find_ruff_bin
                import subprocess
                completed = subprocess.run([find_ruff_bin(), 'check', str(submission)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                output.write(completed.stdout); code = completed.returncode
            elif action == 'typecheck':
                from mypy import api
                stdout, stderr, code = api.run(['--strict','--ignore-missing-imports','--cache-dir',str(submission.parent/'mypy'),str(submission)])
                output.write(stdout+stderr)
            else:
                import pytest
                selectors = [str(trusted / p.split('::')[0]) + ('::'+'::'.join(p.split('::')[1:]) if '::' in p else '') for p in request['selectors']]
                if action == 'learner':
                    selectors = [str(p) for p in submission.rglob('test_learner*.py')]
                    if not selectors: raise ValueError('Create test_learner.py to run your own tests.')
                args = ['-q','--tb=short','-p','no:cacheprovider','--rootdir',str(trusted),'-c','/dev/null','--junitxml',request['report']]
                args += ['-m', 'benchmark' if action=='benchmark' else 'not benchmark']
                args += selectors
                code = int(pytest.main(args))
                if code == 0 and action == 'check' and request.get('module') == '07':
                    from mypy import api
                    stdout, stderr, type_code = api.run(['--strict','--ignore-missing-imports','--cache-dir',str(submission.parent/'mypy'),str(submission / 'exercises_07.py')])
                    output.write(stdout+stderr)
                    code = type_code
                report = Path(request['report'])
                if report.exists():
                    for i, case in enumerate(ET.parse(report).iter('testcase'),1):
                        failure = next((c for c in case if c.tag in {'error','failure','skipped'}),None)
                        cases.append(dict(index=i, passed=failure is None, actual=(failure.text or failure.get('message','Failed'))[-8000:] if failure is not None else 'Passed', expected='All required assertions pass', input=case.get('classname','')+'::'+case.get('name','')))
    except BaseException as error:
        code = 1
        output.write(''.join(traceback.format_exception(error)))
    Path(request['result']).write_text(json.dumps(dict(exitCode=code, cases=cases, output=output.getvalue()[-60000:])))


if __name__ == '__main__': main()
