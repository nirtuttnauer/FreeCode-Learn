#!/bin/sh
set -eu
dpkg -i "${PACKAGE_DIR:-/packages}/freecode_0.7.0~preview1_amd64.deb"
test "$(stat -c '%u:%g:%a' /opt/freecode/chrome-sandbox)" = '0:0:4755'
test "$(readlink /usr/bin/freecode)" = /opt/freecode/FreeCode
grep -q '^Exec=/opt/freecode/FreeCode' /usr/share/applications/freecode.desktop
# Verify every distributed byte matches the tested release candidate. Permissions
# differ only for the root-owned sandbox helper supplied by the .deb.
python3 - <<'PY'
from pathlib import Path
import hashlib
import os
left,right=Path(os.environ.get('PACKAGE_COMPARE_ROOT','/package')),Path('/opt/freecode')
expected={p.relative_to(left) for p in left.rglob('*')}
actual={p.relative_to(right) for p in right.rglob('*')}
assert expected==actual, (expected-actual,actual-expected)
def digest(file):
 h=hashlib.sha256()
 with file.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
 return h.digest()
for name in expected:
 a,b=left/name,right/name
 if a.is_symlink():
  assert a.readlink()==b.readlink(),name
 elif a.is_file():
  assert a.stat().st_size==b.stat().st_size,name
  assert digest(a)==digest(b),name
assert not list((right/'resources').glob('**/progress.json'))
assert not list((right/'resources').glob('**/activity.json'))
# Confirm the case-sensitive runtime directories survive packaging.
assert (right/'resources/bundle/runtimes/x86_64/python/share/terminfo/A').is_dir()
assert (right/'resources/bundle/runtimes/x86_64/python/share/terminfo/a').is_dir()
assert (right/'resources/bundle/runtimes/x86_64/python/share/terminfo/A').stat().st_ino != (right/'resources/bundle/runtimes/x86_64/python/share/terminfo/a').stat().st_ino
print('PASS: installed payload matches tested bundle; root-owned sandbox and launcher verified; no account files')
PY
/opt/freecode/resources/bundle/runtimes/x86_64/python/bin/python3 -I -c 'import sqlite3; print("Bundled SQLite",sqlite3.sqlite_version)'
