#!/usr/bin/env python3
"""Create a fresh, allowlisted open-source snapshot, never copying .git history."""
import argparse
from pathlib import Path
import shutil
from stage_content import stage

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=['runner.py','course_support.py','course_worker.py','build_learning_content.py','build_python_engineer.py','prepare_runtimes.py','prepare_linux_runtimes.py','prepare_course_packages.py','build_app.sh','install_app.py','build_linux.py','assemble_linux_container.py','package_dmg.sh','package_linux.sh','stage_content.py','export_public.py','check_courses.sh','verify_python_engineer.py']


def export(destination):
    destination=Path(destination).resolve()
    if destination.exists(): raise ValueError('Choose a new directory; public export never overwrites existing files.')
    destination.mkdir(parents=True)
    for name in ['Package.swift','.java-version','LICENSE','LICENSE-CONTENT.md','THIRD_PARTY_NOTICES.md','CONTRIBUTING.md']:
        shutil.copy2(ROOT/name,destination/name)
    (destination/'README.md').write_text((ROOT/'PUBLIC_README.md').read_text())
    (destination/'.gitignore').write_text('.build*/\n.cache/\ndist/\nnode_modules/\n__pycache__/\n.DS_Store\napp/linux/renderer.js\n')
    for name in ['Sources','courses','packaging']:
        shutil.copytree(ROOT/name,destination/name,ignore=shutil.ignore_patterns('__pycache__','.DS_Store'))
    for name in ['Read Me.txt','Linux Read Me.txt']:
        (destination/'packaging'/name).write_text('FreeCode — offline original courses\n\nPython Engineer includes 26 modules and five guided projects.\nAll required Python packages are bundled; no account or network connection is needed to study.\nCode: MIT. Lesson prose and diagrams: CC BY 4.0 (Nir Tuttnauer).\nThis public release contains original courses only.\n')
    (destination/'scripts').mkdir()
    for name in SCRIPTS: shutil.copy2(ROOT/'scripts'/name,destination/'scripts'/name)
    (destination/'app/linux').mkdir(parents=True)
    for name in ['package.json','package-lock.json','main.cjs','preload.cjs','backend.py','design.py','index.html','ui.css','ui.js']:
        shutil.copy2(ROOT/'app/linux'/name,destination/'app/linux'/name)
    (destination/'assets').mkdir()
    shutil.copy2(ROOT/'assets/freecode-icon-v2.png',destination/'assets/freecode-icon-v2.png')
    (destination/'tests').mkdir()
    for name in ['test_python_engineer.py','test_course_runner.py','CourseChecks.swift','test_install_app.py','test_runtime_packaging.py','linux_smoke.cjs','linux_course_smoke.cjs','run_linux_container.sh','check_linux_install.sh']:
        if (ROOT/'tests'/name).exists(): shutil.copy2(ROOT/'tests'/name,destination/'tests'/name)
    stage(destination/'data','public')
    (destination/'PUBLIC_README.md').write_text((ROOT/'PUBLIC_README.md').read_text())
    print('Created public source snapshot with no repository history: '+str(destination))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination',type=Path,required=True)
    export(parser.parse_args().destination)
