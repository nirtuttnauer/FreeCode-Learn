#!/usr/bin/env python3
"""Run each complete module suite against its worked implementation, offline."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def verify(identifier):
    import course_support
    import runner
    manifest=json.loads((ROOT/'data/learning/python-engineer/manifest.json').read_text())
    workspace=manifest['workspaces'][identifier]
    step=next(s for s in manifest['steps'].values() if s['workspaceID']==identifier)
    step['selectors']=list(workspace['tests'])
    files=dict(workspace['files']);files[workspace['entrypoint']]=workspace['reference']
    with tempfile.TemporaryDirectory() as directory:
        learning=Path(directory);(learning/'python-engineer').mkdir()
        (learning/'python-engineer/manifest.json').write_text(json.dumps(dict(steps={str(step['id']):step},workspaces={identifier:workspace})))
        return course_support.run(dict(courseStep=str(step['id']),courseFiles=json.dumps(files)),runner.execute,learning)


def main():
    if len(sys.argv)>1:
        print(json.dumps(verify(sys.argv[1])));return
    manifest=json.loads((ROOT/'data/learning/python-engineer/manifest.json').read_text())
    ids=[k for k,w in manifest['workspaces'].items() if w['kind']=='module']
    def run(identifier):
        completed=subprocess.run([sys.executable,'-I','-B',__file__,identifier],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=135)
        try:result=json.loads(completed.stdout)
        except ValueError:result=dict(success=False,output=completed.stderr or completed.stdout)
        return identifier,result
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for identifier,result in pool.map(run,ids):
            results[identifier]=result
            print(('PASS' if result['success'] else 'FAIL'),identifier,result.get('message',''),flush=True)
            if not result['success']:print(result.get('output','')[-8000:],flush=True)
    report=ROOT/'.cache/python-engineer-verification.json';report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(results,indent=2)+'\n')
    raise SystemExit(0 if all(r['success'] for r in results.values()) else 1)


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    main()
