#!/usr/bin/env python3
"""Extract Linux distributions on a case-sensitive Linux filesystem."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import sys
import zipfile


def assemble(inputs, downloads, output):
    inputs, downloads, output = map(Path, [inputs, downloads, output])
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Final assembly must run on Linux to preserve case-sensitive vendor paths.')
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    lock = json.loads((inputs / 'runtime-lock.json').read_text())
    for package in lock['packages']:
        archive = downloads / package['filename']
        digest = hashlib.sha256()
        with archive.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):
                digest.update(block)
        if digest.hexdigest() != package['sha256']:
            raise ValueError('Checksum mismatch: ' + archive.name)
        if package['name'] == 'electron':
            with zipfile.ZipFile(archive) as source:
                for entry in source.infolist():
                    path = PurePosixPath(entry.filename)
                    if path.is_absolute() or '..' in path.parts:
                        raise ValueError('Unsafe Electron path')
                source.extractall(output)
                for entry in source.infolist():
                    mode = entry.external_attr >> 16
                    if mode:
                        (output / entry.filename).chmod(mode & 0o777)
            (output / 'electron').rename(output / 'freecode-bin')
            (output / 'chrome-sandbox').chmod(0o755)
        else:
            target = output / 'resources/bundle/runtimes/x86_64' / package['name']
            target.mkdir(parents=True)
            # Archives are exact pinned vendor bytes, reverified immediately above.
            with tarfile.open(archive) as source:
                members = source.getmembers()
                stripped = []
                for member in members:
                    parts = PurePosixPath(member.name).parts
                    if not parts or len(parts) == 1:
                        continue
                    if PurePosixPath(member.name).is_absolute() or '..' in parts:
                        raise ValueError('Unsafe runtime path')
                    member.name = str(PurePosixPath(*parts[1:]))
                    if member.islnk():
                        member.linkname = str(PurePosixPath(*PurePosixPath(member.linkname).parts[1:]))
                    stripped.append(member)
                source.extractall(target, members=stripped)
    shutil.copytree(inputs / 'resources/app', output / 'resources/app')
    shutil.copytree(inputs / 'resources/bundle', output / 'resources/bundle', dirs_exist_ok=True, symlinks=True)
    for name in ['FreeCode','Read Me.txt','freecode.desktop','manifest.json','runtime-lock.json']:
        shutil.copy2(inputs / name, output / name)
    print('Assembled Linux release:', output, flush=True)

if __name__ == '__main__':
    assemble(*sys.argv[1:])
