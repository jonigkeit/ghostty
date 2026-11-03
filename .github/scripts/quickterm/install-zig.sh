#!/usr/bin/env bash
# Install the version required by this checkout, verified against Zig's manifest.
set -euo pipefail
destination=${1:?Usage: install-zig.sh DESTINATION}
version=$(sed -nE 's/^[[:space:]]*\.minimum_zig_version = "([^"]+)".*/\1/p' build.zig.zon)
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
case $(uname -m) in
  arm64 | aarch64) arch=aarch64 ;;
  x86_64) arch=x86_64 ;;
  *) echo "Unsupported architecture" >&2; exit 1 ;;
esac
case $(uname -s) in
  Darwin) platform=macos ;;
  Linux) platform=linux ;;
  *) echo "Unsupported platform" >&2; exit 1 ;;
esac
mkdir -p "$destination"
destination=$(cd "$destination" && pwd)
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
curl --fail --location --retry 3 https://ziglang.org/download/index.json -o "$temporary/index.json"
url=$(jq -er --arg v "$version" --arg p "$arch-$platform" '.[$v][$p].tarball' "$temporary/index.json")
checksum=$(jq -er --arg v "$version" --arg p "$arch-$platform" '.[$v][$p].shasum' "$temporary/index.json")
[[ "$url" == https://ziglang.org/download/* ]]
[[ "$checksum" =~ ^[0-9a-f]{64}$ ]]
curl --fail --location --retry 3 "$url" -o "$temporary/zig.tar.xz"
printf '%s  %s\n' "$checksum" "$temporary/zig.tar.xz" | shasum -a 256 -c -
tar -xf "$temporary/zig.tar.xz" -C "$destination" --strip-components=1
[[ $("$destination/zig" version) == "$version" ]]
if [[ -n ${GITHUB_PATH:-} ]]; then
  echo "$destination" >> "$GITHUB_PATH"
fi
echo "Installed Zig $version in $destination"
