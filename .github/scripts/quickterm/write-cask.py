#!/usr/bin/env python3
"""Render the tap entry from the actual release archive, never a moving URL."""

import argparse
import hashlib
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    parser.add_argument("version")
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        parser.error("invalid repository")
    if not re.fullmatch(r"[0-9]{14}", args.version):
        parser.error("version must be a UTC timestamp: YYYYMMDDHHMMSS")
    with args.archive.open("rb") as archive:
        checksum = hashlib.file_digest(archive, "sha256").hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f'''cask "ghostty-quickterm" do
  version "{args.version}"
  sha256 "{checksum}"

  url "https://github.com/{args.repository}/releases/download/quickterm-#{{version}}/ghostty-quickterm-universal.zip"
  name "Ghostty Quick Terminal Tabs"
  desc "Terminal emulator with quick terminal tabs from PR 9857"
  homepage "https://github.com/{args.repository}"

  conflicts_with cask: ["ghostty", "ghostty@tip"]
  depends_on macos: ">= :ventura"

  app "Ghostty.app"
  binary "#{{appdir}}/Ghostty.app/Contents/MacOS/ghostty"

  caveats <<~EOS
    This personal build is ad-hoc signed and is not notarized by Apple.
    If macOS blocks it, use Privacy & Security > Open Anyway after verifying the download.
    Upgrade with Homebrew. The in-app updater points to official Ghostty releases.
  EOS
end
''')


if __name__ == "__main__":
    main()
