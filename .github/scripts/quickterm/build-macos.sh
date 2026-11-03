#!/usr/bin/env bash
set -euo pipefail
version=${1:?Usage: build-macos.sh TIMESTAMP_VERSION}
[[ "$version" =~ ^[0-9]{14}$ ]]
sha=$(git rev-parse HEAD)
base_version=$(sed -nE 's/^[[:space:]]*\.version = "([^"]+)".*/\1/p' build.zig.zon)
base_version=${base_version%%-*}
app_version="$base_version-quickterm.$version+${sha:0:9}"

xcodebuild -version
xcrun -f metal
zig build -Doptimize=ReleaseFast -Dcpu=baseline -Demit-macos-app=false \
  -Dxcframework-target=universal -Dversion-string="$app_version"
nu macos/build.nu --configuration ReleaseLocal

app=macos/build/ReleaseLocal/Ghostty.app
plist="$app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :GhosttyCommit $sha" "$plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $(git rev-list --count HEAD)" "$plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $app_version" "$plist"
# Keep updates under Homebrew's control, as in upstream's ReleaseLocal build.
/usr/libexec/PlistBuddy -c 'Set :SUEnableAutomaticChecks false' "$plist"
codesign --force --sign - --options runtime \
  --entitlements macos/GhosttyReleaseLocal.entitlements "$app"
codesign --verify --deep --strict "$app"
lipo -verify_arch arm64 x86_64 "$app/Contents/MacOS/ghostty"
"$app/Contents/MacOS/ghostty" +version
mkdir -p dist/quickterm
ditto -c -k --sequesterRsrc --keepParent "$app" dist/quickterm/ghostty-quickterm-universal.zip
(
  cd dist/quickterm
  shasum -a 256 ghostty-quickterm-universal.zip > SHA256SUMS
)
