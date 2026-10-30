#!/usr/bin/env python3
"""Fail a public release if its data is not exactly the original course inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def audit(data):
    data=Path(data)
    assert json.loads((data/'content-profile.json').read_text())['profile']=='public', 'Public content profile required'
    assert json.loads((data/'catalog.json').read_text())==[], 'Problem library must be empty'
    assert json.loads((data/'playlists.json').read_text())==[], 'Imported playlists must be absent'
    assert not (data/'problems').exists(), 'Imported problem directory must be absent'
    courses=json.loads((data/'learning/courses.json').read_text())
    catalog=json.loads((data/'learning/catalog.json').read_text())
    ids={p['id'] for p in catalog}
    assert ids and all(type(i) is int and i<0 for i in ids)
    assert ids=={i for c in courses for g in c['groups'] for i in g['questionIDs']}
    allowed={'content-profile.json','catalog.json','playlists.json','coverage.json','LICENSE','LICENSE-CONTENT.md','THIRD_PARTY_NOTICES.md','learning/courses.json','learning/catalog.json','learning/README.txt'}
    assets=set()
    for identifier in ids:
        name=f'learning/problems/{identifier}.json';allowed.add(name)
        problem=json.loads((data/name).read_text())
        assert problem['id']==identifier and problem['premium'] is False
        assert not re.search(r'leetcode\.com|github\.com/doocs/',problem.get('sourceURL',''),re.I)
        assets.update(re.findall(r'offline://assets/([a-f0-9]{24}\.[a-zA-Z0-9]+)',problem['statement']))
    allowed.update('assets/'+name for name in assets)
    for course in courses:
        folder=data/'learning'/course['id']
        if (folder/'manifest.json').exists():
            manifest=json.loads((folder/'manifest.json').read_text())
            assert set(map(int,manifest['steps']))<=ids
            allowed.add(f'learning/{course["id"]}/manifest.json')
            allowed.update(f'learning/{course["id"]}/{wid}.json' for wid in manifest['workspaces'])
    actual={str(p.relative_to(data)) for p in data.rglob('*') if p.is_file()}
    assert actual==allowed, f'Unexpected or missing data files: {sorted(actual^allowed)}'
    return dict(profile='public',courses=[c['name'] for c in courses],originalLearningSteps=len(ids),importedProblems=0,importedPlaylists=0,dataFiles=len(actual),
                dataSHA256=hashlib.sha256(''.join(name+':'+hashlib.sha256((data/name).read_bytes()).hexdigest()+'\n' for name in sorted(actual)).encode()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();report=audit(args.data)
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS: public bundle: {report["originalLearningSteps"]} original course steps; zero imported problems/playlists; exact file allowlist')
