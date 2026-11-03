#!/usr/bin/env python3
"""Exercise real Git repositories without network access or GitHub credentials."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("sync.sh").resolve()
BRANCH = "feat/quickterm-with-tab"


class SyncTests(unittest.TestCase):
    def git(self, cwd, *args, check=True):
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            env=self.env,
            check=check,
            text=True,
            capture_output=True,
        ).stdout.strip()

    def commit(self, repo, name, content):
        (repo / name).write_text(content)
        self.git(repo, "add", name)
        self.git(repo, "commit", "-m", f"Update {name}")
        return self.git(repo, "rev-parse", "HEAD")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="quickterm-sync-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = dict(os.environ)
        # Do not inherit the developer's signing requirements or credentials.
        self.env.update({
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Sync Test",
            "GIT_AUTHOR_EMAIL": "sync@example.invalid",
            "GIT_COMMITTER_NAME": "Sync Test",
            "GIT_COMMITTER_EMAIL": "sync@example.invalid",
            "GITHUB_OUTPUT": str(self.root / "output"),
        })
        self.origin = self.root / "origin.git"
        self.ghostty = self.root / "ghostty"
        self.adrum = self.root / "adrum"
        self.work = self.root / "work"
        self.git(self.root, "init", "--bare", f"--initial-branch={BRANCH}", str(self.origin))
        self.git(self.root, "init", "--initial-branch=main", str(self.ghostty))
        self.commit(self.ghostty, "shared", "base\n")
        self.git(self.root, "clone", str(self.ghostty), str(self.adrum))
        self.git(self.adrum, "switch", "-c", BRANCH)
        self.git(self.adrum, "push", str(self.origin), BRANCH)
        self.git(self.root, "clone", str(self.origin), str(self.work))
        self.git(self.work, "remote", "add", "ghostty", str(self.ghostty))
        self.git(self.work, "remote", "add", "adrum", str(self.adrum))
        self.before = self.remote_head()

    def remote_head(self):
        return self.git(self.origin, "rev-parse", f"refs/heads/{BRANCH}")

    def sync(self, success=True):
        result = subprocess.run(
            ["bash", str(SCRIPT)], cwd=self.work, env=self.env,
            text=True, capture_output=True,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_unchanged_does_not_push(self):
        self.sync()
        self.assertEqual(self.remote_head(), self.before)
        self.assertIn("changed=false", (self.root / "output").read_text())

    def test_both_upstreams_are_merged_and_second_run_is_idle(self):
        upstream = self.commit(self.ghostty, "core", "upstream\n")
        tabs = self.commit(self.adrum, "tabs", "tabs\n")
        self.sync()
        for sha in (upstream, tabs):
            self.git(self.origin, "merge-base", "--is-ancestor", sha, BRANCH)
        merges = self.git(self.origin, "rev-list", "--count", "--merges", f"{self.before}..{BRANCH}")
        self.assertEqual(merges, "2")
        first = self.remote_head()
        (self.root / "output").unlink()
        self.sync()
        self.assertEqual(self.remote_head(), first)
        self.assertIn("changed=false", (self.root / "output").read_text())

    def test_each_upstream_independently_triggers_sync(self):
        for repo in (self.ghostty, self.adrum):
            with self.subTest(repo=repo.name):
                sha = self.commit(repo, repo.name, "new\n")
                self.sync()
                self.git(self.origin, "merge-base", "--is-ancestor", sha, BRANCH)

    def test_second_merge_conflict_never_pushes_first_merge(self):
        self.commit(self.ghostty, "shared", "upstream\n")
        self.commit(self.adrum, "shared", "tabs\n")
        result = self.sync(success=False)
        self.assertIn("Nothing has been pushed", result.stderr)
        self.assertEqual(self.remote_head(), self.before)
        self.assertFalse((self.root / "output").exists())
        self.assertEqual(self.git(self.work, "status", "--porcelain"), "")

    def test_dirty_checkout_is_rejected(self):
        (self.work / "shared").write_text("local work\n")
        self.sync(success=False)
        self.assertEqual(self.remote_head(), self.before)
        self.assertEqual((self.work / "shared").read_text(), "local work\n")

    def test_stale_checkout_is_rejected(self):
        sha = self.commit(self.adrum, "new", "concurrent push\n")
        self.git(self.adrum, "push", str(self.origin), BRANCH)
        result = self.sync(success=False)
        self.assertIn("Checkout is stale", result.stderr)
        self.assertEqual(self.remote_head(), sha)

    def test_missing_upstream_branch_does_not_push(self):
        self.commit(self.ghostty, "core", "new\n")
        self.git(self.adrum, "branch", "-m", "renamed")
        self.sync(success=False)
        self.assertEqual(self.remote_head(), self.before)

    def test_wrong_branch_is_rejected(self):
        self.git(self.work, "switch", "-c", "feature/unrelated")
        self.sync(success=False)
        self.assertEqual(self.remote_head(), self.before)


if __name__ == "__main__":
    unittest.main()
