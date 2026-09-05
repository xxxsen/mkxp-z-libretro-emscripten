"""A PFB build must not carry host-only .git indirection into a container."""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


RECIPE = Path(__file__).resolve().parent


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


class SourceSnapshotTests(unittest.TestCase):
    def test_snapshot_preserves_worktree_bytes_and_real_git_identity_without_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            baseline.mkdir()
            git(baseline, "init", "-q")
            git(baseline, "config", "user.name", "Test")
            git(baseline, "config", "user.email", "test@example.invalid")
            (baseline / "source.c").write_text("original", encoding="utf-8")
            (baseline / ".gitignore").write_text("cache/\n", encoding="utf-8")
            git(baseline, "add", ".")
            git(baseline, "commit", "-qm", "fixture")
            worktree = root / "worktree"
            git(baseline, "worktree", "add", "-qb", "fix/test", str(worktree))
            (worktree / "source.c").write_text("modified", encoding="utf-8")
            (worktree / "new.c").write_text("new source", encoding="utf-8")
            (worktree / "cache").mkdir()
            (worktree / "cache/large.bin").write_text("ignored", encoding="utf-8")
            spec = importlib.util.spec_from_file_location("source_snapshot", RECIPE / "source-snapshot.py")
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            output = root / "snapshot"
            module.snapshot(worktree, output)
            self.assertTrue((output / ".git").is_dir())
            self.assertFalse((output / ".git/objects/info/alternates").exists())
            self.assertEqual(git(output, "rev-parse", "HEAD"), git(worktree, "rev-parse", "HEAD"))
            self.assertEqual((output / "source.c").read_text(), "modified")
            self.assertEqual((output / "new.c").read_text(), "new source")
            self.assertFalse((output / "cache").exists())
            self.assertEqual(git(output, "status", "--porcelain"), git(worktree, "status", "--porcelain"))
            self.assertEqual((baseline / "source.c").read_text(), "original")


if __name__ == "__main__":
    unittest.main()
