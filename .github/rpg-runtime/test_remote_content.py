#!/usr/bin/env python3
"""Regression tests for strict remote-content patching."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("patch-remote-content.py")
SPEC = importlib.util.spec_from_file_location("patch_remote_content", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)


class RemoteContentPatchTests(unittest.TestCase):
    def test_fetch_url_join_preserves_exact_remote_path(self) -> None:
        source = '''const std::string FetchBackend::getFileURL(const std::string& filePath) {
  if (filePath == "") {
    return baseUrl;
  }
  return baseUrl + "/" + filePath;
}'''
        patcher = getattr(PATCH, "patch_fetch_backend_cpp", lambda value: value)
        body = patcher(source).replace("FetchBackend::getFileURL", "getFileURL")
        program = '#include <string>\n#include <iostream>\nstd::string baseUrl;\n' + body + '''
int main() {
  for (auto base : {"https://assets.example", "https://assets.example/", "https://assets.example/prefix/"}) {
    baseUrl = base;
    for (auto path : {"/project/game.zip", "/pack/a%20b.zip?version=1"}) {
      std::cout << getFileURL(path) << "\\n";
    }
  }
  baseUrl = "https://assets.example/exact.zip";
  std::cout << getFileURL("") << "\\n";
}'''
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "url-test"
            subprocess.run(["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-x", "c++", "-", "-o", str(binary)],
                           input=program, text=True, check=True, capture_output=True)
            result = subprocess.run([str(binary)], text=True, check=True, capture_output=True)
        self.assertEqual(result.stdout.splitlines(), [
            "https://assets.example/project/game.zip", "https://assets.example/pack/a%20b.zip?version=1",
            "https://assets.example/project/game.zip", "https://assets.example/pack/a%20b.zip?version=1",
            "https://assets.example/prefix/project/game.zip", "https://assets.example/prefix/pack/a%20b.zip?version=1",
            "https://assets.example/exact.zip",
        ])

    def test_manifest_base_url_does_not_use_getline_capacity_as_length(self) -> None:
        source = (
            MODULE_PATH.parents[2]
            / "retroarch/frontend/drivers/platform_emscripten.c"
        ).read_text(encoding="utf-8")

        patched = PATCH.patch_retroarch(source)

        self.assertIn('base_url[strcspn(base_url, "\\r\\n")] = \'\\0\';', patched)
        self.assertNotIn("base_url[len-1]", patched)

    def test_retroarch_requires_a_bounded_power_of_two_chunk_size(self) -> None:
        source = (
            MODULE_PATH.parents[2]
            / "retroarch/frontend/drivers/platform_emscripten.c"
        ).read_text(encoding="utf-8")

        patched = PATCH.patch_retroarch(source)

        self.assertIn('getenv("FETCH_CHUNK_SIZE_BYTES")', patched)
        self.assertIn("fetch_chunk_size < 64 * 1024", patched)
        self.assertIn("fetch_chunk_size > 4 * 1024 * 1024", patched)
        self.assertIn("fetch_chunk_size & (fetch_chunk_size - 1)", patched)
        self.assertIn(PATCH.NEW_BACKEND, patched)
        self.assertNotIn("16*1024*1024", patched)

    def test_fetchfs_never_falls_back_to_a_whole_file_request(self) -> None:
        patched = PATCH.patch_emscripten(PATCH.OLD_HEAD + "\n" + PATCH.OLD_RANGE)

        self.assertIn("FETCHFS_RANGE_REQUIRED", patched)
        self.assertNotIn("wholeFileReq", patched)
        self.assertNotIn("wholeFileData", patched)
        self.assertNotIn("await fetch(url);", patched)

    def test_fetchfs_requires_exact_partial_content(self) -> None:
        patched = PATCH.patch_emscripten(PATCH.OLD_HEAD + "\n" + PATCH.OLD_RANGE)

        self.assertIn("response.status !== 206", patched)
        self.assertIn("response.headers.get('Content-Range') !== expectedContentRange", patched)
        self.assertIn("bytes.byteLength !== end-start", patched)
        self.assertIn("FETCHFS_RANGE_PROTOCOL_INVALID", patched)
        self.assertIn("FETCHFS_RANGE_LENGTH_INVALID", patched)

    def test_patch_fails_closed_after_source_drift(self) -> None:
        with self.assertRaisesRegex(ValueError, "RPG_RUNTIME_FETCHFS_HEAD_INVALID"):
            PATCH.patch_emscripten(PATCH.OLD_HEAD.replace("Accept-Ranges", "Ranges"))


if __name__ == "__main__":
    unittest.main()
