#!/usr/bin/env python3
"""Stage explicit public/personal content; public never traverses private library files."""
import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def stage(destination, profile):
    destination = Path(destination).resolve()
    if destination == ROOT or destination == ROOT/'data' or ROOT.is_relative_to(destination):
        raise ValueError('Choose a staging directory outside the source data.')
    if profile not in {'public','personal'}: raise ValueError('Unknown content profile')
    if destination.exists(): shutil.rmtree(destination)
    if profile == 'personal':
        shutil.copytree(ROOT/'data',destination,ignore=shutil.ignore_patterns('__pycache__','.DS_Store'))
    else:
        source = ROOT/'data/learning'
        courses = json.loads((source/'courses.json').read_text())
        catalog = json.loads((source/'catalog.json').read_text())
        ids = {i for c in courses for g in c['groups'] for i in g['questionIDs']}
        if any(i>=0 for i in ids) or {p['id'] for p in catalog} != ids: raise ValueError('Public courses must reference original learning IDs only.')
        learning=destination/'learning';(learning/'problems').mkdir(parents=True)
        assets=set()
        for identifier in sorted(ids):
            blob=(source/'problems'/f'{identifier}.json').read_bytes()
            problem=json.loads(blob)
            if problem.get('premium') or any(tag in problem['tags'] for tag in ['Database','LeetCode']): raise ValueError('Private content in public course catalog.')
            (learning/'problems'/f'{identifier}.json').write_bytes(blob)
            assets.update(re.findall(r'offline://assets/([a-f0-9]{24}\.[a-zA-Z0-9]+)',problem['statement']))
        for name in ['courses.json','catalog.json','README.txt']:
            shutil.copy2(source/name,learning/name)
        for course in courses:
            pack=source/course['id']
            if (pack/'manifest.json').exists(): shutil.copytree(pack,learning/pack.name)
        (destination/'assets').mkdir()
        for asset in assets: shutil.copy2(ROOT/'data/assets'/asset,destination/'assets'/asset)
        for name in ['catalog.json','playlists.json']:(destination/name).write_text('[]\n')
        (destination/'coverage.json').write_text(json.dumps(dict(profile='public', questions=0, originalLessons=len(catalog), unavailableImages=[]))+'\n')
    (destination/'content-profile.json').write_text(json.dumps(dict(profile=profile))+'\n')
    for name in ['LICENSE','LICENSE-CONTENT.md','THIRD_PARTY_NOTICES.md']:
        shutil.copy2(ROOT/name,destination/name)
    print(f'Staged {profile} content: {destination}')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['public','personal'],default='personal')
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args();stage(args.destination,args.profile)
