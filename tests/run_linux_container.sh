#!/bin/sh
set -eu
if [ -z "${FREECODE_RELEASE_DIR:-}" ]; then
  export FREECODE_RELEASE_DIR=/tmp/release/FreeCode-linux-x86_64
  python3 /scripts/assemble_linux_container.py /input /downloads "$FREECODE_RELEASE_DIR"
fi
export FREECODE_BUNDLE_ROOT="$FREECODE_RELEASE_DIR/resources/bundle"
export FREECODE_TEST_APP="$FREECODE_RELEASE_DIR/resources/app/main.cjs"
# An unbundled Electron host loads the harness, which then requires the exact
# release main process. Packaged Electron ignores external app script arguments.
mkdir -p /tmp/electron/resources
for entry in "$FREECODE_RELEASE_DIR"/*; do
  [ "$(basename "$entry")" = resources ] || cp -a "$entry" /tmp/electron/
done
cp "$FREECODE_RELEASE_DIR/resources/default_app.asar" /tmp/electron/resources/
Xvfb :99 -screen 0 1600x1100x24 -ac -nolisten tcp >/tmp/xvfb.log 2>&1 &
export DISPLAY=:99
sleep 2
exec /tmp/electron/freecode-bin --no-sandbox --disable-gpu "${FREECODE_TEST_HARNESS:-/tests/linux_smoke.cjs}"
