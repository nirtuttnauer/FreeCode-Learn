#!/usr/bin/env python3
"""Local compiler/runner. Only executes code the user explicitly asks to run."""
import argparse
import ast
import collections
import inspect
import json
import os
import platform
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = None
OUTPUT_LIMIT = 256_000


def cancel(*_):
    if ACTIVE is not None:
        try:
            os.killpg(ACTIVE.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    raise SystemExit(130)


def limits(cpu_seconds=15, file_bytes=4 * 1024 * 1024):
    os.setsid()
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))


def execute(command, directory, stdin='', timeout=10, compiling=False):
    global ACTIVE
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as inp:
        inp.write(stdin.encode())
        inp.seek(0)
        ACTIVE = subprocess.Popen(command, cwd=directory, stdin=inp, stdout=out,
                                  stderr=subprocess.STDOUT,
                                  preexec_fn=lambda: limits(120, 256 * 1024 * 1024) if compiling or timeout == 120 else limits())
        deadline, failure = time.monotonic() + timeout, None
        while ACTIVE.poll() is None:
            if time.monotonic() > deadline:
                failure = f'Time limit exceeded ({timeout}s).'
            elif os.fstat(out.fileno()).st_size > OUTPUT_LIMIT:
                failure = 'Output limit exceeded (256 KB).'
            if failure:
                os.killpg(ACTIVE.pid, signal.SIGKILL)
                break
            time.sleep(0.025)
        ACTIVE.wait()
        status = ACTIVE.returncode
        # Descendants must not outlive a run, even when the parent exits first.
        try:
            os.killpg(ACTIVE.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        ACTIVE = None
        out.seek(0)
        output = out.read(OUTPUT_LIMIT).decode(errors='replace')
    if failure:
        raise RuntimeError(failure + '\n' + output)
    if status:
        raise RuntimeError(output or f'Process exited with status {status}.')
    return output


def tool(name):
    runtimes = ROOT / 'runtimes'
    if runtimes.exists() or (ROOT.name == 'Resources' and ROOT.parent.name == 'Contents'):
        java_home = 'java' if sys.platform.startswith('linux') else 'java/Contents/Home'
        paths = {'node': 'node/bin/node', 'java': f'{java_home}/bin/java',
                 'javac': f'{java_home}/bin/javac', 'clang++': 'bin/clang++'}
        candidate = runtimes / platform.machine() / paths[name]
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        raise RuntimeError(f'Bundled {name} is missing. Reinstall PracticeCode from the full package.')
    # jenv's project selection works even when launched by Finder without shell init.
    if name in {'java', 'javac'}:
        jenv = shutil.which('jenv') or '/opt/homebrew/bin/jenv'
        if Path(jenv).is_file():
            try:
                home = subprocess.check_output([jenv, 'prefix'], cwd=ROOT, stderr=subprocess.DEVNULL, timeout=3).decode().strip()
                candidate = Path(home) / 'bin' / name
                if candidate.is_file():
                    return str(candidate)
            except (OSError, subprocess.SubprocessError):
                pass
        home = os.environ.get('JAVA_HOME')
        if home and (Path(home) / 'bin' / name).is_file():
            return str(Path(home) / 'bin' / name)
    paths = [Path('/opt/homebrew/bin') / name, Path('/usr/local/bin') / name]
    found = shutil.which(name)
    if found:
        paths.append(Path(found))
    for path in paths:
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    raise RuntimeError(f'{name} is not installed. Install its runtime and reopen the app.')


def signature(reference, language):
    if language == 'cpp':
        part = reference.partition('public:')[2]
        match = re.search(r'([\w:<>, &*]+?)\s+(\w+)\s*\(([^)]*)\)\s*\{', part)
    elif language == 'java':
        match = re.search(r'public\s+(?:static\s+)?([\w<>\[\], ?]+?)\s+(\w+)\s*\(([^)]*)\)\s*\{', reference)
    elif language == 'javascript':
        match = re.search(r'(?:var|let|const)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\(([^)]*)\)', reference)
        if match:
            return {'name': match[1], 'params': match[2], 'returnType': ''}
        match = re.search(r'function\s+(\w+)\s*\(([^)]*)\)', reference)
        if match:
            return {'name': match[1], 'params': match[2], 'returnType': ''}
        return None
    else:
        return None
    if not match:
        return None
    return {'returnType': match[1].strip(), 'name': match[2], 'params': match[3].strip()}


def starter(reference, language):
    if language == 'python':
        try:
            tree = ast.parse(reference)
            classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
            if not classes:
                return None
            cls = classes[0]
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and (not n.name.startswith('_') or n.name == '__init__')]
            if not methods:
                return None
            for method in methods:
                method.body = [ast.Raise(exc=ast.Call(func=ast.Name(id='NotImplementedError', ctx=ast.Load()), args=[], keywords=[]), cause=None)]
                method.decorator_list = []
            cls.body = methods
            return 'from typing import *\n\n' + ast.unparse(ast.fix_missing_locations(cls)) + '\n'
        except SyntaxError:
            return None
    sig = signature(reference, language)
    if not sig:
        return None
    if language == 'javascript':
        return f"var {sig['name']} = function({sig['params']}) {{\n    throw new Error('Implement your solution');\n}};\n"
    if language == 'cpp':
        return f"class Solution {{\npublic:\n    {sig['returnType']} {sig['name']}({sig['params']}) {{\n        throw runtime_error(\"Implement your solution\");\n    }}\n}};\n"
    return f"class Solution {{\n    public {sig['returnType']} {sig['name']}({sig['params']}) {{\n        throw new UnsupportedOperationException(\"Implement your solution\");\n    }}\n}}\n"


class ListNode:
    def __init__(self, val=0, next=None):
        self.val, self.next = val, next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def list_node(values):
    dummy = current = ListNode()
    for value in values or []:
        current.next = ListNode(value)
        current = current.next
    return dummy.next


def tree_node(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = collections.deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        for side in ['left', 'right']:
            if i < len(values) and values[i] is not None:
                child = TreeNode(values[i])
                setattr(node, side, child)
                queue.append(child)
            i += 1
    return root


def serialize(value):
    if isinstance(value, ListNode):
        values, visited = [], set()
        while value:
            if id(value) in visited:
                raise ValueError('Cycle in returned linked list')
            visited.add(id(value))
            values.append(value.val)
            value = value.next
        return values
    if isinstance(value, TreeNode):
        values, queue, visited = [], collections.deque([value]), set()
        while queue:
            node = queue.popleft()
            if node is None:
                values.append(None)
            else:
                if id(node) in visited:
                    raise ValueError('Cycle in returned tree')
                visited.add(id(node))
                values.append(node.val)
                queue.extend([node.left, node.right])
        while values and values[-1] is None:
            values.pop()
        return values
    if isinstance(value, (list, tuple, set, range)):
        return [serialize(x) for x in value]
    return value


def python_worker(request):
    import bisect, functools, heapq, itertools, math, random
    namespace = {}
    for module in [typing, collections, bisect, functools, heapq, itertools, math, random]:
        namespace.update({k: v for k, v in vars(module).items() if not k.startswith('_')})
    namespace.update({'ListNode': ListNode, 'TreeNode': TreeNode, '__name__': '__solution__'})
    exec('from __future__ import annotations\n' + request['code'], namespace)
    args = request['args']
    if 'Solution' not in namespace:
        if len(args) == 2 and isinstance(args[0], list) and args[0] and isinstance(args[0][0], str):
            operations, inputs = args
            obj, outputs = namespace[operations[0]](*inputs[0]), [None]
            for op, params in zip(operations[1:], inputs[1:]):
                outputs.append(serialize(getattr(obj, op)(*params)))
            print('\n__OFFLINE_RESULT__' + json.dumps(outputs))
            return
        raise ValueError('Function mode requires a Solution class or design-problem operation arrays. Use Program mode for a custom harness.')
    methods = [n for n in vars(namespace['Solution']) if not n.startswith('_')]
    name = request.get('method') or methods[0]
    method = getattr(namespace['Solution'](), name)
    hints = getattr(method, '__annotations__', {})
    parameters = list(inspect.signature(method).parameters)
    for i, key in enumerate(parameters):
        if i >= len(args):
            break
        annotation = str(hints.get(key, ''))
        if 'ListNode' in annotation:
            args[i] = [list_node(v) for v in args[i]] if 'List[' in annotation else list_node(args[i])
        elif 'TreeNode' in annotation:
            args[i] = tree_node(args[i])
    value = method(*args)
    # Void functions are compared against their first mutated argument.
    if value is None and (hints.get('return') in {'None', 'NoneType', None}) and args:
        value = args[0]
    print('\n__OFFLINE_RESULT__' + json.dumps(serialize(value)))


def split_parameters(text):
    result, depth, start = [], 0, 0
    for i, char in enumerate(text):
        depth += char == '<'
        depth -= char == '>'
        if char == ',' and depth == 0:
            result.append(text[start:i].strip())
            start = i + 1
    if text.strip():
        result.append(text[start:].strip())
    return result


def literal(value, type_name, language):
    t = type_name.replace('const ', '').replace('&', '').strip()
    if value is None:
        return 'nullptr' if language == 'cpp' else 'null'
    if language == 'cpp' and t.startswith('vector<'):
        inner = t[t.find('<') + 1:t.rfind('>')]
        return t + '{' + ','.join(literal(v, inner, language) for v in value) + '}'
    if language == 'java' and t.endswith('[]'):
        return 'new ' + t + '{' + ','.join(literal(v, t[:-2], language) for v in value) + '}'
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        if t == 'char':
            if len(value) != 1:
                raise ValueError('A char parameter needs one character.')
            return "'" + value.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r') + "'"
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, (int, float)):
        return str(value) + ('LL' if language == 'cpp' and ('long' in t or abs(value) > 2147483647) else 'L' if language == 'java' and ('long' in t or abs(value) > 2147483647) else '')
    raise ValueError(f'Automatic {language} harness does not support {type_name}. Use Program mode with your own harness.')


CPP_HEADER = r'''
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <unordered_map>
#include <unordered_set>
#include <map>
#include <set>
#include <queue>
#include <stack>
#include <numeric>
#include <cmath>
#include <climits>
#include <functional>
#include <iomanip>
#include <stdexcept>
using namespace std;
template<class T> void emit(const vector<T>& v);
inline void emit(const string& v) { cout << quoted(v); }
inline void emit(char v) { emit(string(1,v)); }
inline void emit(bool v) { cout << (v ? "true" : "false"); }
template<class T> void emit(const T& v) { cout << v; }
template<class T> void emit(const vector<T>& v) { cout << '['; bool first=true; for (const auto& x:v) { if (!first) cout << ','; first=false; emit(x); } cout << ']'; }
'''

JAVA_HEADER = r'''
import java.util.*;
import java.util.stream.*;
import java.lang.reflect.Array;
class OfflineJSON {
    static String emit(Object x) {
        if (x == null) return "null";
        if (x instanceof String || x instanceof Character) return "\"" + x.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t") + "\"";
        if (x instanceof Number || x instanceof Boolean) return x.toString();
        List<String> parts = new ArrayList<>();
        if (x.getClass().isArray()) { for (int i=0;i<Array.getLength(x);i++) parts.add(emit(Array.get(x,i))); }
        else if (x instanceof Iterable) { for (Object v : (Iterable<?>)x) parts.add(emit(v)); }
        else throw new IllegalArgumentException("Unsupported output type; use Program mode");
        return "[" + String.join(",", parts) + "]";
    }
}
'''


def compiled_harness(request, args, language):
    sig = signature(request.get('reference', ''), language)
    if not sig:
        raise ValueError('This signature needs a custom harness. Switch to Program mode.')
    params = split_parameters(sig['params'])
    if len(params) != len(args):
        raise ValueError(f"Expected {len(params)} arguments, received {len(args)}.")
    declarations, names = [], []
    for i, (param, value) in enumerate(zip(params, args)):
        match = re.match(r'(.+?)[\s&*]+(\w+)\s*$', param)
        if not match:
            raise ValueError('Unsupported parameter declaration; use Program mode.')
        type_name = match[1].strip()
        # References bind to local variables, never to temporary arrays.
        declarations.append(f'{type_name.replace("const ", "").replace("&", "").strip()} p{i} = {literal(value, type_name, language)};')
        names.append(f'p{i}')
    call = f"solution.{sig['name']}({','.join(names)})"
    value = call if sig['returnType'] != 'void' else names[0] if names else 'null'
    void_call = call + ';' if sig['returnType'] == 'void' else ''
    if language == 'cpp':
        return CPP_HEADER + request['code'] + '\nint main(){ Solution solution; ' + ''.join(declarations) + void_call + '\ncout << "\\n__OFFLINE_RESULT__"; emit(' + value + '); }\n'
    return JAVA_HEADER + request['code'] + '\nclass Main { public static void main(String[] ignored) { Solution solution = new Solution(); ' + ''.join(declarations) + void_call + '\nSystem.out.println("\\n__OFFLINE_RESULT__" + OfflineJSON.emit(' + value + ')); }}\n'


def run_code(request, directory, args=None):
    language, code = request['language'], request['code']
    function = request.get('mode') == 'function'
    stdin = request.get('stdin', '')
    if function and language == 'python':
        payload = {**request, 'args': args}
        path = directory / 'worker.json'
        path.write_text(json.dumps(payload))
        return execute([sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--python-worker', str(path)], directory)
    if function and language == 'javascript':
        sig = signature(request.get('reference', '') or code, language)
        if not sig:
            raise ValueError('Automatic JavaScript tests need a named function. Use Program mode for design classes or a custom harness.')
        code += f"\nconsole.log('\\n__OFFLINE_RESULT__' + JSON.stringify({sig['name']}(...{json.dumps(args)})));\n"
    elif function:
        code = compiled_harness(request, args, language)
    if language == 'javascript':
        path = directory / 'solution.js'
        path.write_text(code)
        return execute([tool('node'), str(path)], directory, stdin)
    if language == 'python':
        path = directory / 'solution.py'
        path.write_text(code)
        return execute([sys.executable, '-I', '-B', str(path)], directory, stdin)
    if language == 'cpp':
        path = directory / 'solution.cpp'
        path.write_text(code)
        execute([tool('clang++'), '-std=c++20', '-O1', str(path), '-o', str(directory / 'solution')], directory, timeout=120, compiling=True)
        return execute([str(directory / 'solution')], directory, stdin)
    if language == 'java':
        path = directory / 'Main.java'
        path.write_text(code)
        execute([tool('javac'), '-encoding', 'UTF-8', str(path)], directory, timeout=30, compiling=True)
        return execute([tool('java'), '-Xmx256m', '-cp', str(directory), 'Main'], directory, stdin)
    raise ValueError('Unknown language')


def equal(actual, expected):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, int) and isinstance(expected, int):
        return actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(actual - expected) <= 1e-5 * max(1, abs(expected))
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def run_request(request):
    if request.get('mode') == 'course':
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import course_support
        return course_support.run(request, execute, ROOT / 'data/learning')
    if len(request.get('code', '')) > 1_000_000:
        raise ValueError('Code exceeds 1 MB.')
    started, cases, logs = time.monotonic(), [], []
    with tempfile.TemporaryDirectory(prefix='offline-practice-') as temp:
        directory = Path(temp)
        if request.get('language') == 'sql':
            payload = directory / 'sql.json'
            payload.write_text(json.dumps(request))
            output = execute([sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--sql-worker', str(payload)], directory)
            result = json.loads(output)
            return dict(success=True, message=f"SQLite query returned {len(result['rows'])} rows" + (' (first 500)' if result['truncated'] else ''), output=json.dumps(result, indent=2, ensure_ascii=False), cases=[], duration=time.monotonic()-started)
        if request.get('mode') != 'function':
            output = run_code(request, directory)
            return dict(success=True, message='Program finished', output=output, cases=[], duration=time.monotonic()-started)
        tests = json.loads(request.get('tests', '[]'))
        if not isinstance(tests, list) or not 1 <= len(tests) <= 50:
            raise ValueError('Provide 1–50 test cases as a JSON array. Each needs "args" and "expected".')
        for i, case in enumerate(tests):
            if not isinstance(case, dict) or not isinstance(case.get('args'), list) or 'expected' not in case:
                raise ValueError(f'Case {i+1} needs an "args" array and an "expected" value.')
            output = run_code(request, directory, case['args'])
            before, marker, result = output.rpartition('__OFFLINE_RESULT__')
            if not marker:
                raise ValueError('No result from function harness. Use Program mode to debug a custom harness.')
            actual = json.loads(result.strip())
            if before.strip():
                logs.append(before.strip())
            expected = case['expected']
            passed = equal(actual, expected)
            # Explicit opt-in for problems permitting multiple answer orders.
            if case.get('unordered') is True and isinstance(actual, list) and isinstance(expected, list):
                passed = sorted(json.dumps(x, sort_keys=True) for x in actual) == sorted(json.dumps(x, sort_keys=True) for x in expected)
            cases.append(dict(index=i+1, passed=passed, actual=json.dumps(actual, ensure_ascii=False), expected=json.dumps(expected, ensure_ascii=False), input=json.dumps(case['args'], ensure_ascii=False)))
    count = sum(c['passed'] for c in cases)
    return dict(success=count == len(cases), message=f'{count} of {len(cases)} local tests passed', output='\n'.join(logs)[-30000:], cases=cases, duration=time.monotonic()-started)


def prepare_library(root):
    count = collections.Counter()
    for path in (root / 'problems').glob('*.json'):
        problem = json.loads(path.read_text())
        problem['starters'] = {}
        for lang, reference in problem['references'].items():
            code = starter(reference, lang)
            if code:
                problem['starters'][lang] = code
                count[lang] += 1
        if 'javascript' not in problem['starters'] and 'python' in problem['references']:
            try:
                tree = ast.parse(problem['references']['python'])
                cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Solution')
                method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_'))
                params = ', '.join(a.arg for a in method.args.args if a.arg != 'self')
                problem['starters']['javascript'] = f"var {method.name} = function({params}) {{\n    throw new Error('Implement your solution');\n}};\n"
                count['javascript'] += 1
            except (SyntaxError, StopIteration):
                pass
        path.write_text(json.dumps(problem, ensure_ascii=False))
    print(dict(count))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path)
    parser.add_argument('--python-worker', type=Path)
    parser.add_argument('--sql-worker', type=Path)
    parser.add_argument('--prepare-library', type=Path)
    options = parser.parse_args()
    if options.prepare_library:
        prepare_library(options.prepare_library)
    elif options.python_worker:
        python_worker(json.loads(options.python_worker.read_text()))
    elif options.sql_worker:
        import sqlite3
        request = json.loads(options.sql_worker.read_text())
        if not request['code'].strip() or all(not line.strip() or line.strip().startswith('--') for line in request['code'].splitlines()):
            raise ValueError('Write a SQL query before running.')
        connection = sqlite3.connect(':memory:')
        connection.set_authorizer(lambda action, *_: sqlite3.SQLITE_DENY if action in {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH} else sqlite3.SQLITE_OK)
        connection.executescript(request.get('stdin', ''))
        cursor = connection.execute(request['code'])
        rows = cursor.fetchmany(501) if cursor.description else []
        print(json.dumps(dict(columns=[c[0] for c in cursor.description] if cursor.description else [], rows=rows[:500], truncated=len(rows)>500), ensure_ascii=False))
        connection.close()
    else:
        signal.signal(signal.SIGTERM, cancel)
        signal.signal(signal.SIGINT, cancel)
        try:
            request = json.loads(options.request.read_text()) if options.request else json.load(sys.stdin)
            result = run_request(request)
        except Exception as exc:
            result = dict(success=False, message='Run failed', output=str(exc)[-30000:], cases=[])
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
