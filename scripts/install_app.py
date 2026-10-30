#!/usr/bin/env python3
"""Install a verified build at the fixed path used by the user's Dock."""
import argparse
import plistlib
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

IDENTIFIER = 'local.offlinepractice.mac'
PROCESS = r'^.*/FreeCode\.app/Contents/MacOS/OfflinePractice$'


def verify_bundle(app):
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') != IDENTIFIER:
        raise RuntimeError(f'Refusing to replace a different application: {app}')
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)


def is_running():
    return subprocess.run(['pgrep', '-f', PROCESS], capture_output=True).returncode == 0


def quit_running_app():
    subprocess.run(['osascript', '-e', f'tell application id "{IDENTIFIER}" to quit'], check=True)
    deadline = time.monotonic() + 10
    while is_running():
        if time.monotonic() >= deadline:
            raise RuntimeError('FreeCode did not quit; the installed copy was left unchanged.')
        time.sleep(0.1)


def install_app(source, destination):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    if source == destination:
        raise ValueError('The build and installation paths must be different.')
    verify_bundle(source)
    if destination.exists():
        verify_bundle(destination)
    # Stage on the installation volume; a copy failure never changes the old app.
    with tempfile.TemporaryDirectory(prefix='.FreeCode-update-', dir=destination.parent) as temporary:
        staged = Path(temporary) / 'FreeCode.app'
        subprocess.run(['ditto', str(source), str(staged)], check=True)
        verify_bundle(staged)
        running = is_running()
        if running:
            quit_running_app()
        backup = destination.with_name(f'.FreeCode-previous-{uuid.uuid4().hex}.app')
        try:
            if destination.exists():
                destination.rename(backup)
            try:
                staged.rename(destination)
            except OSError:
                if backup.exists():
                    backup.rename(destination)
                raise
        finally:
            # Normal termination saves the user's work; reopen the installed copy.
            if running and destination.exists():
                subprocess.run(['open', str(destination)], check=True)
        if backup.exists():
            shutil.rmtree(backup)
    subprocess.run(['/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister',
                    '-f', str(destination)], check=True)
    print(f'Installed {destination}' + (' and reopened it' if running else ''))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--destination', type=Path, default=Path('/Applications/FreeCode.app'))
    args = parser.parse_args()
    install_app(args.source, args.destination)
