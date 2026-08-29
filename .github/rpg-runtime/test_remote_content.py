#!/usr/bin/env python3
"""Regression tests for strict remote-content patching."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("patch-remote-content.py")
SPEC = importlib.util.spec_from_file_location("patch_remote_content", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)


class RemoteContentPatchTests(unittest.TestCase):
    def test_retroarch_requires_a_bounded_power_of_two_chunk_size(self) -> None:
        source = "\n".join(
            (
                PATCH.OLD_FETCH_DECLARATIONS,
                PATCH.OLD_FETCH_GUARD,
                PATCH.OLD_FETCH_REQUIREMENTS,
                PATCH.OLD_BACKEND,
            )
        )

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
