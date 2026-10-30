#!/usr/bin/env python3
"""Prepare checksum-pinned, relocatable macOS runtimes for both app slices."""
import concurrent.futures
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'packaging/runtimes-lock.json'
CACHE = ROOT / '.cache/runtime-downloads'
OUTPUT = ROOT / '.cache/runtime-bundle'


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def download(package):
    path = CACHE / package['filename']
    if path.exists() and digest(path) == package['sha256']:
        return path
    partial = path.with_suffix(path.suffix + '.download')
    subprocess.run(['curl', '-fLsS', '--http1.1', '--retry', '3', '--retry-all-errors', '--connect-timeout', '30', '--max-time', '1800',
                    package['url'], '-o', str(partial)], check=True)
    if digest(partial) != package['sha256']:
        partial.unlink()
        raise RuntimeError(f"Checksum mismatch: {path.name}")
    partial.replace(path)
    return path


def validate_archive(archive):
    """Reject traversal and writes through archive-created symbolic links."""
    with tarfile.open(archive) as source:
        members = source.getmembers()
    links = set()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ValueError(f'Unsafe archive path: {member.name}')
        if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
            raise ValueError(f'Unsupported archive entry: {member.name}')
        if member.issym() or member.islnk():
            target = PurePosixPath(member.linkname)
            joined = path.parent / target if member.issym() else target
            depth = 0
            for part in joined.parts:
                depth += -1 if part == '..' else 0 if part == '.' else 1
                if depth < 1:
                    raise ValueError(f'Escaping archive link: {member.name}')
            if target.is_absolute():
                raise ValueError(f'Absolute archive link: {member.name}')
            if member.issym():
                links.add(path)
    for member in members:
        if any(parent in links for parent in PurePosixPath(member.name).parents):
            raise ValueError(f'Archive writes through symlink: {member.name}')


def main():
    lock = LOCK.read_bytes()
    marker = OUTPUT / 'manifest.json'
    if marker.exists() and marker.read_bytes() == lock:
        print(f'Using prepared runtimes: {OUTPUT}', flush=True)
        return
    packages = json.loads(lock)['packages']
    CACHE.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        archives = list(pool.map(download, packages))
    with tempfile.TemporaryDirectory(prefix='runtimes-', dir=ROOT / '.cache') as temp:
        staging = Path(temp)
        for package, archive in zip(packages, archives):
            if package['arch'] == 'shared':
                target = staging / 'sources'
                target.mkdir(exist_ok=True)
                shutil.copy2(archive, target / archive.name)
                continue
            validate_archive(archive)
            target = staging / package['arch'] / package['name']
            target.mkdir(parents=True)
            subprocess.run(['/usr/bin/tar', '-xf', str(archive), '--strip-components=1', '-C', str(target)], check=True)
        for arch, target in [('arm64', 'aarch64'), ('x86_64', 'x86_64')]:
            wrapper = staging / arch / 'bin/clang++'
            wrapper.parent.mkdir()
            wrapper.write_text('#!/bin/sh\nset -eu\n'
                'RUNTIME_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)\n'
                f'export ZIG_GLOBAL_CACHE_DIR="${{HOME}}/Library/Caches/PracticeCode/zig/{arch}"\n'
                'export ZIG_LOCAL_CACHE_DIR="$ZIG_GLOBAL_CACHE_DIR/local"\n'
                f'exec "$RUNTIME_DIR/zig/zig" c++ -target {target}-macos.14.0 "$@"\n')
            wrapper.chmod(0o755)
        (staging / 'manifest.json').write_bytes(lock)
        (staging / 'README.txt').write_text(
            'PracticeCode bundled runtimes\n\n'
            'Python: python-build-standalone (PSF and bundled dependency licenses).\n'
            'Node.js: MIT and dependency licenses.\n'
            'Temurin OpenJDK 21: GPLv2 with Classpath Exception; corresponding source\n'
            'archive is included in sources/. Vendor legal notices are in java/Contents/Home/legal/.\n'
            'Zig and its portable C++ toolchain: MIT and dependency licenses.\n'
            'All original vendor licenses and notices are retained within each distribution.\n'
            'manifest.json records original download URLs, versions and SHA-256 checksums.\n'
            'C++ builds target macOS 14 and use the system libSystem only; no Apple SDK required.\n'
            'Compiler caches are created in ~/Library/Caches/PracticeCode/, outside the signed app.\n')
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        staging.rename(OUTPUT)
    print(f'Prepared bundled runtimes: {OUTPUT}', flush=True)


if __name__ == '__main__':
    main()
