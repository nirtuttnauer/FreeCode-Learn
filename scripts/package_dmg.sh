#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
zsh scripts/build_app.sh --universal
APP="${PWD}/dist/FreeCode.app"
ARCHITECTURES=$(lipo -archs "$APP/Contents/MacOS/OfflinePractice")
if [[ " $ARCHITECTURES " != *" arm64 "* || " $ARCHITECTURES " != *" x86_64 "* ]]; then
    print -u2 "Universal binary required; found: $ARCHITECTURES"
    exit 1
fi
codesign --verify --deep --strict "$APP"
VERSION=$(/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' "$APP/Contents/Info.plist")
STAGING=$(mktemp -d "${PWD}/.cache/FreeCode-dmg.XXXXXX")
trap 'rm -rf -- "$STAGING"' EXIT
ditto "$APP" "$STAGING/FreeCode.app"
ln -s /Applications "$STAGING/Applications"
cp 'packaging/Read Me.txt' "$STAGING/Read Me.txt"
DMG="${PWD}/dist/FreeCode-${VERSION}-universal.dmg"
hdiutil create -ov -volname FreeCode -srcfolder "$STAGING" -fs HFS+ -format UDZO "$DMG"
hdiutil verify "$DMG"
(
    cd "${DMG:h}"
    shasum -a 256 "${DMG:t}" > "${DMG:t}.sha256"
)
print "Packaged ${DMG}"
