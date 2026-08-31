import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = "bf5f525e864b162bea0789d46932e5f800b80076"


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_identity_uses_the_organization_and_core_tag_namespace(self) -> None:
        contract = json.loads((ROOT / "retrom-fork.json").read_text(encoding="utf-8"))
        workflow = (ROOT / ".github/workflows/rpg-runtime-release.yml").read_text(encoding="utf-8")

        self.assertEqual(
            contract["forkRepository"],
            "https://github.com/retrom-project/mkxp-z-libretro-emscripten",
        )
        self.assertIn("^retrom-core-(f2efc98|g[0-9a-f]{12})", contract["releaseTagPattern"])
        self.assertIn('"retrom-core-f2efc98-r*"', workflow)
        self.assertNotIn('"rpg-runtime-f2efc98-r*"', workflow)

    def test_release_rejects_merges_after_immutable_checkpoint(self) -> None:
        workflow = (ROOT / ".github/workflows/rpg-runtime-release.yml").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn(f'{CHECKPOINT}.."$GITHUB_SHA"', workflow)
        self.assertIn("git rev-list --min-parents=2", workflow)
        self.assertIn("must\n  use squash merge", agents)
        self.assertIn(CHECKPOINT, agents)


if __name__ == "__main__":
    unittest.main()
