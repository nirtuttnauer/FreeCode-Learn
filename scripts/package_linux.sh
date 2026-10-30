#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
if [[ "${1:-}" == "--no-build" ]]; then
  [[ -f dist/linux-input/resources/app/renderer.js ]] || exit 1
elif (( $# == 0 )); then
  python3 scripts/build_linux.py
else
  print -u2 "Usage: zsh scripts/package_linux.sh [--no-build]"
  exit 1
fi
mkdir -p .cache/linux-package-output
# All final runtime extraction and packaging happens on Linux. Vendor archives
# contain distinct uppercase/lowercase paths that macOS cannot preserve.
docker run --rm --platform linux/amd64 --network none --shm-size 1g \
  -v "$PWD/dist/linux-input:/input:ro" \
  -v "$PWD/.cache/runtime-downloads:/downloads:ro" \
  -v "$PWD/scripts:/scripts:ro" \
  -v "$PWD/tests:/tests:ro" \
  -v "$PWD/dist/linux-deb:/skeleton:ro" \
  -v "$PWD/.cache/linux-package-output:/output" \
  -e OFFLINE_PRACTICE_WORK_DIR=/tmp/practicecode-fresh \
  practicecode-linux-check:0.7 sh -eu -c '
    export FREECODE_RELEASE_DIR=/tmp/release/PracticeCode-linux-x86_64
    python3 /scripts/assemble_linux_container.py /input /downloads "$FREECODE_RELEASE_DIR"
    python3 /scripts/audit_public_bundle.py --data "$FREECODE_RELEASE_DIR/resources/bundle/data" --output /output/content-audit.json
    rm -f /output/report.json
    if [ ! -d /input/resources/bundle/data/problems ]; then
      FREECODE_TEST_HARNESS=/tests/linux_course_smoke.cjs sh /tests/run_linux_container.sh
      cp /output/course-report.json /output/report.json
    else
      sh /tests/run_linux_container.sh
    fi
    python3 -c '\''import json; r=json.load(open("/output/report.json")); assert not r.get("failure") and not r["errors"]'\''
    mkdir -p /tmp/deb/opt
    cp -a /skeleton/. /tmp/deb/
    cp -a "$FREECODE_RELEASE_DIR" /tmp/deb/opt/practicecode
    chown -R 0:0 /tmp/deb
    chmod 4755 /tmp/deb/opt/practicecode/chrome-sandbox
    dpkg-deb --root-owner-group -Zxz -z3 --build /tmp/deb /output/practicecode_0.7.0~preview1_amd64.deb
    PACKAGE_COMPARE_ROOT="$FREECODE_RELEASE_DIR" PACKAGE_DIR=/output sh /tests/check_linux_install.sh
    tar --owner=0 --group=0 -czf /output/PracticeCode-0.7.0-preview.1-linux-x86_64.tar.gz -C /tmp/release PracticeCode-linux-x86_64
    dpkg-deb --info /output/practicecode_0.7.0~preview1_amd64.deb
  '
cp .cache/linux-package-output/practicecode_0.7.0~preview1_amd64.deb dist/
cp .cache/linux-package-output/PracticeCode-0.7.0-preview.1-linux-x86_64.tar.gz dist/
cp .cache/linux-package-output/report.json dist/PracticeCode-linux-verification.json
cp .cache/linux-package-output/content-audit.json dist/PracticeCode-linux-content-audit.json
(cd dist && shasum -a 256 'practicecode_0.7.0~preview1_amd64.deb' PracticeCode-0.7.0-preview.1-linux-x86_64.tar.gz > PracticeCode-linux-SHA256SUMS.txt)
