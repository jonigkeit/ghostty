# Ghostty with Quick Terminal tabs

This fork integrates [PR #9857](https://github.com/ghostty-org/ghostty/pull/9857)
on `feat/quickterm-with-tab`. It tracks `ghostty/main` and
`adrum/feat/quickterm-with-tab` using merge commits. The latter is the actual
source branch of the PR; there is no `adrum/quickterm-with-tab` branch.

## Install through Homebrew

After the first successful **Release Quick Terminal** workflow, this repository
also serves as a Homebrew tap. The workflow creates
`Casks/ghostty-quickterm.rb` with an immutable release URL and SHA-256 checksum.
No separate tap repository or personal access token is required.

Quit Ghostty and use another terminal for the switch:

```sh
brew tap jonigkeit/ghostty https://github.com/jonigkeit/ghostty.git
brew uninstall --cask ghostty
brew install --cask jonigkeit/ghostty/ghostty-quickterm
```

The cask deliberately conflicts with `ghostty` and `ghostty@tip`: they all
install `Ghostty.app` and the `ghostty` command. Uninstalling without `--zap`
preserves your Ghostty configuration. If you use `ghostty@tip`, uninstall
that cask instead. This setup does not automatically replace your existing app.

Updates:

```sh
brew update
brew upgrade --cask jonigkeit/ghostty/ghostty-quickterm
```

These builds are ad-hoc signed, not signed with an Apple Developer ID or
notarized. If macOS blocks the app, verify the download and use **System Settings
→ Privacy & Security → Open Anyway**. Automatic in-app updates are disabled;
do not use **Check for Updates**, which still targets official Ghostty releases.

To return to the official build, quit Ghostty and run:

```sh
brew uninstall --cask jonigkeit/ghostty/ghostty-quickterm
brew install --cask ghostty
```

## Automation

- **Release Quick Terminal** (`quickterm-release.yml`) builds pushes to
  `feat/quickterm-with-tab`, or can be run manually on that branch. Cask-only
  commits do not cause another build. A reusable entry point accepts the exact
  commit produced by the sync workflow.
- The build uses the Zig version in `build.zig.zon`, verified against Zig's
  download manifest, and the macOS 26 GitHub runner's Xcode. It compiles both
  Apple Silicon and Intel, uses `ReleaseLocal`, verifies code signing and both
  architectures, and runs a CLI smoke check before uploading.
- Each successful build produces an immutable `quickterm-YYYYMMDDHHMMSS`
  prerelease, a universal ZIP, `SHA256SUMS`, and an updated cask. Build jobs have
  read-only repository permissions; publication uses `contents: write`.
- **Sync Quick Terminal upstreams** (`quickterm-sync.yml`) runs daily at
  **05:23 UTC** and can be run manually. It fetches both upstream branches,
  skips commits already integrated, and merges new commits with `--no-ff`.
  Only after both merges succeed does it push the integration branch.
- The sync explicitly calls the release workflow after a change: pushes made
  with `GITHUB_TOKEN` do not trigger other push workflows.
- Conflicts, missing upstream refs, and concurrent pushes fail the run. Nothing
  is force-pushed, and no issue or PR is opened. Resolve a conflict locally on
  the integration branch and push; that push starts a release. If an upstream
  branch is rewritten, review its history manually before continuing to merge.
- If the branch changes during a build, publication stops to avoid downgrading
  the tap. Re-run **Release Quick Terminal** on the current branch. If a push
  races with the final cask commit, the release may exist without a cask update;
  re-run the workflow to publish the current source and update the cask.

### Activate the daily schedule

GitHub runs scheduled workflows only from the repository's default branch.
For this fork, use `feat/quickterm-with-tab` as the default branch and enable
Actions. This also makes Homebrew clone the branch containing `Casks/`.
Keep `main` available as the upstream baseline.

If you keep `main` as the default branch, the daily schedule will not run until
the sync workflow is installed on that branch. The release workflow must also
be available there for the reusable call. The tap instructions above assume
that the feature branch is the default branch.

The repository's Actions token needs write access to contents, and branch
rules must allow its integration and cask commits. No other secrets are used.
GitHub can delay scheduled jobs, and disables schedules in public repositories
after 60 days without repository activity; re-enable the workflow if needed.

## Local checks and builds in Podman

Do not install build tools on the host. With an existing Podman machine running,
build the isolated tool image and run it against a read-only checkout:

```sh
podman build -t localhost/ghostty-quickterm-checks \
  -f .github/scripts/quickterm/Containerfile .github/scripts/quickterm
podman run --rm --name ghostty-quickterm-checks \
  --cpus 2 --memory 4g \
  -v "$PWD:/source:ro" localhost/ghostty-quickterm-checks
```

The container copies the checkout into its own filesystem, runs the sync tests,
ShellCheck, actionlint, formatting checks and cask syntax validation, then
downloads the required Zig compiler and builds `libghostty-vt`. Tools, caches,
and build output remain inside Podman. The host checkout and installed Ghostty
app are unchanged. Remove the tool image when no longer needed:

```sh
podman image rm localhost/ghostty-quickterm-checks
```

Podman on macOS runs Linux containers. These can compile the portable Zig core,
but cannot run Xcode or build the native AppKit/SwiftUI macOS application.
The macOS release workflow therefore requires a disposable GitHub macOS runner;
it installs dependencies only on that runner. It produces
`macos/build/ReleaseLocal/Ghostty.app` and
`dist/quickterm/ghostty-quickterm-universal.zip` there. If all builds must use
Podman, the native macOS release cannot be produced with this setup.

For a fresh clone, add the upstreams once:

```sh
git remote add ghostty https://github.com/ghostty-org/ghostty.git
git remote add adrum https://github.com/adrum/ghostty.git
```

The container's sync tests use temporary Git repositories without contacting
GitHub or changing the host checkout.
