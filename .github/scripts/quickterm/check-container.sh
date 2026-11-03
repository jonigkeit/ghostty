#!/usr/bin/env bash
set -euo pipefail

python3 .github/scripts/quickterm/test_sync.py
shellcheck .github/scripts/quickterm/*.sh
actionlint .github/workflows/quickterm-release.yml .github/workflows/quickterm-sync.yml
prettier --check .github/workflows/quickterm-release.yml .github/workflows/quickterm-sync.yml QUICKTERM.md
git diff --check

# Validate generated Ruby without installing or changing a host Homebrew tap.
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT
printf 'release archive fixture\n' > "$fixture/archive.zip"
python3 .github/scripts/quickterm/write-cask.py jonigkeit/ghostty \
  20261103000000 "$fixture/archive.zip" "$fixture/ghostty-quickterm.rb"
ruby -c "$fixture/ghostty-quickterm.rb"

bash .github/scripts/quickterm/install-zig.sh /opt/quickterm-zig
export PATH="/opt/quickterm-zig:$PATH"
# The portable terminal library can be built on Linux. AppKit/SwiftUI and
# Xcode's macOS app bundle cannot be built in a Linux Podman container.
zig build -Demit-lib-vt -Doptimize=ReleaseFast -j2
