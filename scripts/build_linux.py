#!/usr/bin/env python3
"""Prepare Linux build inputs; final runtime extraction runs on Linux."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import stage_content
import prepare_course_packages

ROOT = Path(__file__).resolve().parent.parent
PREPARED = ROOT / '.cache/linux-runtime-inputs'
STAGE = ROOT / 'dist/linux-input'

def build():
    if not (PREPARED / 'manifest.json').exists():
        subprocess.run([sys.executable, str(ROOT / 'scripts/prepare_linux_runtimes.py')], check=True)
    subprocess.run(['npm', 'run', '--prefix', str(ROOT / 'app/linux'), 'build'], check=True)
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    app = STAGE / 'resources/app'
    app.mkdir(parents=True)
    for name in ['package.json','main.cjs','preload.cjs','backend.py','design.py','index.html','ui.css','renderer.js']:
        shutil.copy2(ROOT / 'app/linux' / name, app / name)
    shutil.copy2(ROOT / 'assets/practicecode-icon-v2.png', app / 'icon.png')
    bundle = STAGE / 'resources/bundle'
    profile = os.environ.get('FREECODE_CONTENT_PROFILE')
    if not profile:
        marker=ROOT/'data/content-profile.json'
        profile=json.loads(marker.read_text())['profile'] if marker.exists() else 'personal'
    stage_content.stage(bundle / 'data', profile)
    (bundle / 'scripts').mkdir()
    shutil.copy2(ROOT / 'scripts/runner.py', bundle / 'scripts/runner.py')
    for name in ['course_support.py','course_worker.py']:
        shutil.copy2(ROOT/'scripts'/name,bundle/'scripts'/name)
    shutil.copytree(prepare_course_packages.prepare('linux-x86_64'),bundle/'course-packages/x86_64')
    (bundle / 'runtimes/x86_64/bin').mkdir(parents=True)
    shutil.copy2(PREPARED / 'runtimes/x86_64/bin/clang++', bundle / 'runtimes/x86_64/bin/clang++')
    shutil.copytree(PREPARED / 'runtimes/sources', bundle / 'runtimes/sources')
    for name in ['manifest.json','README.txt']:
        shutil.copy2(PREPARED / 'runtimes' / name, bundle / 'runtimes' / name)
    for name in ['manifest.json']:
        if (PREPARED/name).exists():
            shutil.copy2(PREPARED/name, STAGE/name)
    shutil.copy2(ROOT / 'packaging/linux-runtimes-lock.json', STAGE/'runtime-lock.json')
    shutil.copy2(ROOT/'packaging/Linux Read Me.txt', STAGE/'Read Me.txt')
    launcher = STAGE/'PracticeCode'
    launcher.write_text('#!/bin/sh\nset -eu\nFREECODE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$FREECODE_DIR/practicecode-bin" "$@"\n')
    launcher.chmod(0o755)
    desktop = '[Desktop Entry]\nType=Application\nName=PracticeCode\nComment=Offline coding practice and learning\nExec=/opt/practicecode/PracticeCode %U\nIcon=practicecode\nTerminal=false\nCategories=Development;Education;\nStartupWMClass=PracticeCode\n'
    (STAGE/'practicecode.desktop').write_text(desktop)
    package_root = ROOT/'dist/linux-deb'
    if package_root.exists(): shutil.rmtree(package_root)
    (package_root/'DEBIAN').mkdir(parents=True)
    (package_root/'DEBIAN/control').write_text('Package: practicecode\nVersion: 0.7.0~preview1\nArchitecture: amd64\nMaintainer: PracticeCode\nSection: education\nPriority: optional\nDepends: libc6 (>= 2.35), fonts-liberation, libgtk-3-0 | libgtk-3-0t64, libnss3, libasound2 | libasound2t64, libgbm1, libxss1, libatk-bridge2.0-0, libx11-xcb1, libdrm2, libxkbcommon0, libcups2, libgl1\nDescription: PracticeCode offline coding practice\n Local questions, learning tracks and bundled coding runtimes.\n')
    # Package under /opt without duplicating the large bundle on the host.
    (package_root/'usr/share/applications').mkdir(parents=True)
    (package_root/'usr/share/applications/practicecode.desktop').write_text(desktop)
    (package_root/'usr/share/icons/hicolor/512x512/apps').mkdir(parents=True)
    shutil.copy2(app/'icon.png', package_root/'usr/share/icons/hicolor/512x512/apps/practicecode.png')
    (package_root/'usr/bin').mkdir(parents=True)
    os.symlink('/opt/practicecode/PracticeCode', package_root/'usr/bin/practicecode')
    print('Prepared Linux inputs:', STAGE)

if __name__ == '__main__': build()
