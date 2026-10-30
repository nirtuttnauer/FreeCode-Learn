#!/usr/bin/env python3
"""Compile the editable Python Engineer course to PracticeCode's offline format."""
import ast
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT / 'courses/python-engineer'
SOURCE = COURSE / 'source'
OUTPUT = ROOT / 'data/learning'


def inline(text):
    text = html.escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'\[([^]]+)\]\(([^)]+)\)', lambda m: m[1] + (' <small>(optional reading: ' + m[2] + ')</small>' if m[2].startswith('https://') else ''), text)


def markdown(text):
    """Small offline renderer: escaped prose, headings, code, lists and tables."""
    output, code, table = [], None, False
    for line in text.splitlines():
        if line.startswith('```'):
            if code is None:
                code = []
            else:
                output.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        if line.startswith('|'):
            if re.fullmatch(r'[| :\-]+', line):
                continue
            if not table:
                output.append('<table>'); table = True
            output.append('<tr>' + ''.join('<td>' + inline(x.strip()) + '</td>' for x in line.strip('|').split('|')) + '</tr>')
            continue
        if table:
            output.append('</table>'); table = False
        if line.startswith('#'):
            level = min(6, len(line) - len(line.lstrip('#')))
            output.append(f'<h{level}>' + inline(line.lstrip('# ')) + f'</h{level}>')
        elif line.strip() and line.strip() != '---':
            output.append('<p>' + inline(line) + '</p>')
    if table: output.append('</table>')
    if code is not None: raise ValueError('Unclosed Markdown code fence')
    return '\n'.join(output)


def read(path):
    return path.read_text() if path.exists() else ''


def prepared_tests(path):
    source = path.read_text()
    tree = ast.parse(source)
    lines = source.splitlines()
    insertions = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith('test_'): continue
        if any(isinstance(n, ast.Call) and (isinstance(n.func, ast.Name) and n.func.id == 'timed' or isinstance(n.func, ast.Attribute) and n.func.attr == 'perf_counter') for n in ast.walk(node)):
            insertions.append((min([node.lineno]+[d.lineno for d in node.decorator_list])-1, node.col_offset))
    for line, indent in sorted(insertions,reverse=True): lines.insert(line,' '*indent+'@pytest.mark.benchmark')
    return '\n'.join(lines)+'\n'


def test_selectors(path, symbol):
    tree = ast.parse(path.read_text())
    found = []
    for node in tree.body:
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith(('Test', 'test_')):
            continue
        if any(isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'm' and n.attr == symbol for n in ast.walk(node)):
            found.append(path.name + '::' + node.name)
    return found or [path.name]


def main():
    global COURSE, SOURCE, OUTPUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--course',type=Path,default=COURSE)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    COURSE=args.course.resolve();SOURCE=COURSE/'source';OUTPUT=args.output.resolve()
    config=json.loads((COURSE/'course.json').read_text())
    course_id,course_name=config['id'],config['name']
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',course_id):raise ValueError('Use a lowercase course ID.')
    existing_catalog=json.loads(read(OUTPUT/'catalog.json') or '[]')
    occupied=[p['id'] for p in existing_catalog]
    (OUTPUT / 'problems').mkdir(parents=True, exist_ok=True)
    bundle = OUTPUT / course_id
    bundle.mkdir(exist_ok=True)
    id_file = COURSE / 'ids.json'
    identifiers = json.loads(read(id_file) or '{}')
    manifest = dict(schemaVersion=1, id=course_id, name=course_name, workspaces={}, steps={})
    summaries, groups = [], []

    def add(key, workspace, title, body, selectors, reference='', difficulty='Medium'):
        if key not in identifiers:
            identifiers[key] = min([-3000] + occupied + list(identifiers.values())) - 1
        identifier = identifiers[key]
        version = hashlib.sha256(json.dumps(workspace, sort_keys=True).encode()).hexdigest()
        meta = dict(courseID=course_id, workspaceID=workspace['id'], entrypoint=workspace['entrypoint'], checkGroup=key, version=version)
        record = dict(id=identifier, title=title, slug=key, url='', difficulty=difficulty,
                      tags=[course_name, workspace['title']], premium=False, statement=body,
                      references={'python':reference} if reference else {}, starters={'python':workspace['files'][workspace['entrypoint']]},
                      samples=[], sourceURL='', missingImages=[], course=meta)
        (OUTPUT / 'problems' / f'{identifier}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        summaries.append({k:record[k] for k in ['id', 'title', 'slug', 'difficulty', 'premium', 'tags']})
        manifest['steps'][str(identifier)] = dict(**meta, selectors=selectors, id=identifier, title=title)
        return identifier

    for folder in sorted(SOURCE.glob('[0-9]*_*')):
        number = folder.name.split('_')[0]
        exercise = folder / f'exercises_{number}.py'
        if not exercise.exists(): continue
        text = exercise.read_text()
        title = read(folder / 'README.md').splitlines()[0].lstrip('# ').split(' — ',1)[-1]
        files = {exercise.name:text}
        workspace = dict(id=course_id+'-' + number, title=title, entrypoint=exercise.name, files=files,
                         tests={p.name:prepared_tests(p) for p in folder.glob('test_*.py')}, demo=read(folder / f'lesson_{number}.py'),
                         reference=read(folder / f'solutions_{number}.py'), module=number, kind='module')
        manifest['workspaces'][workspace['id']] = workspace
        concepts = markdown(read(folder / 'README.md'))
        ids = []
        for node in ast.parse(text).body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) or node.name.startswith('_'): continue
            snippet = '\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])
            if 'NotImplementedError' not in snippet and '<- fix this' not in snippet: continue
            contract = ast.get_docstring(node) or f'Implement {node.name} according to its tests and the module contract.'
            key = 'python-' + number + '-' + node.name.lower()
            body = f'<p><strong>{html.escape(course_name)} · {html.escape(title)}</strong></p><h2>Build {html.escape(node.name)}</h2>'
            body += markdown(contract)
            body += '<h3>Work through this step</h3><ol><li>Read the contract and identify its boundary cases.</li><li>Run the demonstration to explore the concept.</li><li>Edit the module file; focus on this step’s function or class.</li><li>Run required checks, then explain one design decision in Notes.</li></ol>'
            body += '<details><summary>Hint</summary><p>Start with the smallest example in the contract. Read the named failing test; separate the normal behavior from validation and edge cases. Related helpers share this module workspace.</p></details>'
            body += '<details><summary>Module concepts & examples</summary>' + concepts + '</details>'
            body += '<details><summary>Required check source</summary><pre><code>' + html.escape(workspace['tests'][f'test_{number}.py']) + '</code></pre></details>'
            body += '<h3>Review your understanding</h3><p>What invariant does your implementation preserve? Which edge case would a simpler implementation miss?</p><p>Required checks assess your code. Benchmark timings and written reasoning are reported separately. Files are shared by this module’s steps; editing them makes those steps need verification again.</p>'
            ids.append(add(key, workspace, node.name.replace('_',' '), body, test_selectors(folder / f'test_{number}.py', node.name), workspace['reference']))
        groups.append(dict(name=number + ' · ' + title, questionIDs=ids))

    for folder in sorted((SOURCE / 'projects').glob('[0-9]*_*')):
        text = (folder / 'SPEC.md').read_text()
        title = text.splitlines()[0].lstrip('# ')
        files = {str(p.relative_to(folder)):p.read_text() for p in (folder / 'src').rglob('*.py')}
        entry = next((p for p in files if p.endswith('__init__.py')), next(iter(files)))
        workspace = dict(id=course_id+'-project-' + folder.name[:2], title=title, entrypoint=entry, files=files,
                         tests={'test_acceptance.py':(folder/'test_acceptance.py').read_text()}, demo='', reference='', kind='project')
        milestone_file = COURSE / 'project-checks' / (folder.name + '.json')
        checks = json.loads(read(milestone_file) or '{}')
        for p in (COURSE / 'project-checks' / folder.name).glob('*.py'):
            workspace['tests'][p.name] = p.read_text()
        manifest['workspaces'][workspace['id']] = workspace
        sections = re.split(r'(?m)^## (Milestone \d+[^\n]*)\n', text)
        ids = []
        for i in range(1,len(sections),2):
            heading, detail = sections[i], sections[i+1].split('\n## Going further')[0].split('\n## What')[0]
            number = re.search(r'Milestone (\d+)', heading)[1]
            selected = checks.get(number)
            if not selected: raise ValueError(f'Missing required milestone checks: {folder.name}/{number}')
            body = '<p><strong>'+html.escape(course_name)+' · Project</strong></p>' + markdown('# ' + heading + '\n' + detail)
            body += '<h3>Build in small increments</h3><ol><li>List the public interfaces and invariants required by this milestone.</li><li>Implement one behavior and write a small test in a test_learner.py file.</li><li>Run your tests, then run the required milestone checks.</li><li>Record a tradeoff and failure case in Notes before moving on.</li></ol><details><summary>Hint</summary><p>Keep dependencies injectable. Prefer in-memory stores, fake clocks, and scripted clients so behavior is reproducible offline. Use the traceback to find the first missing behavior.</p></details><details><summary>Complete project specification</summary>' + markdown(text) + '</details><p>No complete worked solution is provided. Passing checks verifies this milestone’s executable contract; deployment and optional extensions are ungraded.</p>'
            body += '<details><summary>App check interfaces & required scenarios</summary><p>These tests define the concrete interfaces used in this app. Read them before choosing file names and method signatures.</p>' + ''.join('<h4>'+html.escape(name)+'</h4><pre><code>'+html.escape(code)+'</code></pre>' for name,code in workspace['tests'].items()) + '</details>'
            ids.append(add('python-project-' + folder.name[:2] + '-' + number, workspace, title.split(' — ')[0] + ' · ' + heading, body, selected, difficulty='Hard'))
        groups.append(dict(name='Project · ' + title, questionIDs=ids))
    ids = [x['id'] for x in summaries]
    if len(ids) != len(set(ids)) or any(not g['questionIDs'] for g in groups): raise ValueError('Empty group or duplicate ID')
    manifest['version'] = hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    (bundle / 'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2) + '\n')
    for workspace in manifest['workspaces'].values():
        (bundle / (workspace['id'] + '.json')).write_text(json.dumps(workspace['files'],indent=2) + '\n')
    course = dict(id=course_id, name=course_name, summary=f'{len(groups)-5} modules and five guided projects. Python language depth, engineering, concurrency, web systems, data and security. All checks run offline.',groups=groups)
    for name, additions in [('catalog.json',summaries), ('courses.json',[course])]:
        current = json.loads(read(OUTPUT/name) or '[]')
        current = [x for x in current if (x.get('id') != course_id if name=='courses.json' else x['id'] not in identifiers.values())]
        (OUTPUT/name).write_text(json.dumps(current+additions,ensure_ascii=False,indent=2)+'\n')
    id_file.write_text(json.dumps(identifiers,indent=2,sort_keys=True)+'\n')
    print(f'{course_name}: {sum(w["kind"]=="module" for w in manifest["workspaces"].values())} modules, {sum(w["kind"]=="project" for w in manifest["workspaces"].values())} projects, {len(ids)} executable steps.')


if __name__ == '__main__': main()
