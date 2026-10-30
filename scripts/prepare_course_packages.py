#!/usr/bin/env python3
"""Install exact hash-pinned wheels into offline, architecture-specific app resources."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'packaging/course-packages-lock.json'
CACHE = ROOT / '.cache/course-wheels'


def fetch(wheel):
    path = CACHE / wheel['filename']
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == wheel['sha256']: return path
    partial = path.with_suffix('.download')
    subprocess.run(['curl','-fLsS','--retry','3','--connect-timeout','30','--max-time','600',wheel['url'],'-o',str(partial)],check=True)
    if hashlib.sha256(partial.read_bytes()).hexdigest() != wheel['sha256']:
        partial.unlink()
        raise ValueError('Wheel checksum mismatch: ' + path.name)
    partial.replace(path)
    return path


def prepare(platform):
    lock = json.loads(LOCK.read_text())
    target = ROOT / '.cache/course-packages' / platform
    signature = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    if (target/'manifest.json').exists() and json.loads((target/'manifest.json').read_text()).get('lockSHA256') == signature:
        print('Using offline course packages: ' + platform); return target
    wheels = lock['targets'][platform]
    CACHE.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(fetch,wheels))
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temp:
        stage = Path(temp)/'packages'; stage.mkdir()
        for wheel,path in zip(wheels,paths):
            with zipfile.ZipFile(path) as archive:
                for entry in archive.infolist():
                    parts = PurePosixPath(entry.filename).parts
                    if not parts or entry.filename.startswith('/') or '..' in parts or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('Unsafe wheel path: ' + entry.filename)
                    if entry.is_dir(): continue
                    relative = PurePosixPath(*parts)
                    if parts[0].endswith('.data'):
                        if len(parts)<3: continue
                        if parts[1] in {'purelib','platlib'}: relative = PurePosixPath(*parts[2:])
                        elif parts[1]=='scripts': relative=PurePosixPath('bin',*parts[2:])
                        else: continue
                    destination = stage / str(relative)
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    destination.write_bytes(archive.read(entry))
                    destination.chmod(0o755 if entry.external_attr >> 16 & 0o111 else 0o644)
        (stage/'manifest.json').write_text(json.dumps(dict(lockSHA256=signature, wheels=wheels),indent=2)+'\n')
        if platform.startswith('macos'):
            for path in stage.rglob('*'):
                if path.is_file() and (path.suffix in {'.so','.dylib'} or path.name in {'ruff'}):
                    subprocess.run(['codesign','--force','--sign','-',str(path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        if target.exists(): shutil.rmtree(target)
        shutil.move(str(stage),target)
    print(f'Prepared {len(wheels)} offline packages: {platform}')
    return target


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform',choices=['macos-arm64','macos-x86_64','linux-x86_64'],required=True)
    prepare(parser.parse_args().platform)
