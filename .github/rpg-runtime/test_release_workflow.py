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

    def test_pfb_candidate_uses_locked_builder_and_calling_user(self) -> None:
        recipe = ROOT / ".github/rpg-runtime"
        candidate = (recipe / "build-candidate.sh").read_text(encoding="utf-8")
        builder = (recipe / "build-web.sh").read_text(encoding="utf-8")

        self.assertIn('candidate_descriptor.py" prepare', candidate)
        self.assertIn('candidate_descriptor.py" finalize', candidate)
        self.assertIn('test -f "$output/rpg-runtime-release.json"', candidate)
        self.assertIn('verify-release.py"', builder)
        self.assertIn('--source "$source_root"', builder)
        self.assertIn('patch-runtime-status.py"', builder)
        self.assertIn('source-snapshot.py" --source "$root" --output "$work/input"', builder)
        self.assertEqual(builder.count('--volume "$source_input:/input:ro"'), 3)
        self.assertIn('build-cache.py" restore', builder)
        self.assertIn('build-cache.py" store', builder)
        self.assertIn("MESON_PACKAGE_CACHE_DIR=/cache", builder)
        self.assertIn("--core-id mkxp", candidate)
        self.assertIn("stage1_image=ubuntu@sha256:", builder)
        self.assertIn("emscripten_image=emscripten/emsdk@sha256:", builder)
        self.assertIn("--stage1-in-container", builder)
        self.assertIn("--core-in-container", builder)
        self.assertIn("--frontend-in-container", builder)
        self.assertIn('"$artifacts/stage1/."', builder)
        self.assertIn('"$artifacts/mkxp-z_libretro.a"', builder)
        self.assertIn("if ((jobs > 4))", builder)
        self.assertIn('find "$work/core" -mindepth 1 -delete', builder)
        self.assertIn("libtool python3 ruby", builder)
        self.assertIn("cmake==3.28.3 meson==1.3.2", builder)
        self.assertIn('setpriv --reuid="$1" --regid="$2"', builder)
        self.assertIn("XDG_CONFIG_HOME=/work/frontend/user-config", builder)
        self.assertIn("c = 'emcc'", builder)
        self.assertNotIn("RUBYOPT=-rset", builder)
        self.assertNotIn("/var/run/docker.sock", builder)


if __name__ == "__main__":
    unittest.main()
