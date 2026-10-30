#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
BUILD_OPTIONS=(--configuration release --scratch-path .build)
PROFILE=personal
if [[ -f data/content-profile.json ]]; then
    PROFILE=$(python3 -c 'import json; print(json.load(open("data/content-profile.json"))["profile"])')
fi
if [[ "${1:-}" == "--public" ]]; then
    PROFILE=public
    shift
fi
if [[ "${1:-}" == "--universal" && $# == 1 ]]; then
    BUILD_OPTIONS=(--configuration release --scratch-path .build-universal --arch arm64 --arch x86_64)
elif (( $# > 0 )); then
    print -u2 "Usage: zsh scripts/build_app.sh [--public] [--universal]"
    exit 1
fi
swift build "${BUILD_OPTIONS[@]}"
python3 scripts/prepare_runtimes.py
APP="${PWD}/dist/PracticeCode.app"
if [[ -d "${PWD}/dist/Offline Practice.app" && ! -e "$APP" ]]; then
    mv "${PWD}/dist/Offline Practice.app" "$APP"
fi
mkdir -p "${APP}/Contents/MacOS" "${APP}/Contents/Resources"
BIN=$(swift build "${BUILD_OPTIONS[@]}" --show-bin-path)
cp "${BIN}/OfflinePractice" "${APP}/Contents/MacOS/OfflinePractice"
python3 scripts/stage_content.py --profile "$PROFILE" --destination "${APP}/Contents/Resources/data"
mkdir -p "${APP}/Contents/Resources/scripts"
cp scripts/runner.py "${APP}/Contents/Resources/scripts/runner.py"
cp scripts/course_support.py scripts/course_worker.py "${APP}/Contents/Resources/scripts/"
mkdir -p "${APP}/Contents/Resources/course-packages"
for ARCH in arm64 x86_64; do
    python3 scripts/prepare_course_packages.py --platform "macos-${ARCH}"
    rm -rf "${APP}/Contents/Resources/course-packages/${ARCH}"
    ditto ".cache/course-packages/macos-${ARCH}" "${APP}/Contents/Resources/course-packages/${ARCH}"
done
cp .java-version "${APP}/Contents/Resources/.java-version"
rm -rf "${APP}/Contents/Resources/runtimes"
ditto .cache/runtime-bundle "${APP}/Contents/Resources/runtimes"
ICONSET="${PWD}/.cache/practicecode.iconset"
mkdir -p "$ICONSET"
for SIZE in 16 32 128 256 512; do
    sips -z "$SIZE" "$SIZE" assets/practicecode-icon-v2.png --out "$ICONSET/icon_${SIZE}x${SIZE}.png" >/dev/null
    DOUBLE=$((SIZE * 2))
    sips -z "$DOUBLE" "$DOUBLE" assets/practicecode-icon-v2.png --out "$ICONSET/icon_${SIZE}x${SIZE}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "${APP}/Contents/Resources/practicecode.icns"
cat > "${APP}/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>OfflinePractice</string>
<key>CFBundleIdentifier</key><string>local.offlinepractice.mac</string>
<key>CFBundleName</key><string>PracticeCode</string>
<key>CFBundleDisplayName</key><string>PracticeCode</string>
<key>CFBundleIconFile</key><string>practicecode.icns</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>0.7.0</string>
<key>CFBundleVersion</key><string>8</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSSupportsAutomaticTermination</key><false/>
<key>NSHumanReadableCopyright</key><string>PracticeCode code: MIT. Original teaching content: CC BY 4.0. Third-party notices included with bundled content.</string>
</dict></plist>
PLIST
codesign --force --sign - "${APP}"
print "Built ${APP}"
python3 scripts/install_app.py "$APP"
