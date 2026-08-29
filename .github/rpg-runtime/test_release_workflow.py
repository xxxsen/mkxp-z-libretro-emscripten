from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = "bf5f525e864b162bea0789d46932e5f800b80076"


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_rejects_merges_after_immutable_checkpoint(self) -> None:
        workflow = (ROOT / ".github/workflows/rpg-runtime-release.yml").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn(f'{CHECKPOINT}.."$GITHUB_SHA"', workflow)
        self.assertIn("git rev-list --min-parents=2", workflow)
        self.assertIn("must\n  use squash merge", agents)
        self.assertIn(CHECKPOINT, agents)


if __name__ == "__main__":
    unittest.main()
