#!/usr/bin/env python3
"""Download pinned Linux distributions and prepare platform-neutral build inputs."""
import concurrent.futures
import json
from pathlib import Path
import shutil
import tempfile

import prepare_runtimes as shared

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'packaging/linux-runtimes-lock.json'
OUTPUT = ROOT / '.cache/linux-runtime-inputs'


def main():
    lock = LOCK.read_bytes()
    if (OUTPUT / 'manifest.json').is_file() and (OUTPUT / 'manifest.json').read_bytes() == lock:
        print(f'Using prepared Linux runtime inputs: {OUTPUT}', flush=True)
        return
    packages = json.loads(lock)['packages']
    shared.CACHE.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(shared.download, packages))
    with tempfile.TemporaryDirectory(prefix='linux-runtimes-', dir=ROOT / '.cache') as temp:
        stage = Path(temp)
        wrapper = stage / 'runtimes/x86_64/bin/clang++'
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text('#!/bin/sh\nset -eu\n'
                           'RUNTIME_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)\n'
                           'export ZIG_GLOBAL_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/FreeCode/zig"\n'
                           'export ZIG_LOCAL_CACHE_DIR="$ZIG_GLOBAL_CACHE_DIR/local"\n'
                           'exec "$RUNTIME_DIR/zig/zig" c++ -target x86_64-linux-gnu.2.31 -mcpu=baseline "$@"\n')
        wrapper.chmod(0o755)
        sources = stage / 'runtimes/sources'
        sources.mkdir()
        # The same pinned OpenJDK release is already distributed with the macOS bundle.
        source_package = next(p for p in json.loads(shared.LOCK.read_text())['packages'] if p['name'] == 'java-source')
        shutil.copy2(shared.download(source_package), sources / source_package['filename'])
        (stage / 'manifest.json').write_bytes(lock)
        (stage / 'runtimes/manifest.json').write_bytes(lock)
        (stage / 'runtimes/README.txt').write_text('FreeCode Linux runtimes: Python/SQLite (PSF), Node (MIT), Temurin OpenJDK (GPLv2 + Classpath Exception), Zig/C++ (MIT and bundled licenses). Original vendor notices remain in each distribution; corresponding OpenJDK source is in sources/. URLs and SHA-256 checksums are in manifest.json. Compiler caches are outside the app.\n')
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        stage.rename(OUTPUT)
    print(f'Prepared Linux runtime inputs: {OUTPUT}', flush=True)


if __name__ == '__main__':
    main()
