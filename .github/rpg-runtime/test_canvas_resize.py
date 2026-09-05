"""Run the patched upstream C callbacks with explicit browser/render ownership."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


RECIPE = Path(__file__).resolve().parent
ROOT = RECIPE.parents[1]


def patch_module():
    spec = importlib.util.spec_from_file_location("patch_canvas", RECIPE / "patch-canvas-resize.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source():
    return (ROOT / "retroarch/frontend/drivers/platform_emscripten.c").read_text(encoding="utf-8")


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index("\n}\n", start) + 3]


HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define PLATFORM_SETVAL(type, addr, value) (*(addr) = (value))
#define PLATFORM_GETVAL(type, addr) (*(addr))
#define RARCH_ERR(...) ((void)0)
#define EMSCRIPTEN_RESULT_SUCCESS 0
struct platform { int canvas_width, canvas_height; double device_pixel_ratio; } data;
struct platform *emscripten_platform_data = &data;
int browser_thread = 1, mutations = 0, actual_width = 64, actual_height = 64;
int emscripten_set_canvas_element_size(const char *target, int width, int height) {
  assert(!browser_thread && "ResizeObserver must not mutate or synchronously proxy the thread-owned canvas");
  assert(strcmp(target, "#canvas") == 0);
  actual_width = width; actual_height = height; mutations++;
  return 0;
}
int emscripten_get_canvas_element_size(const char *target, int *width, int *height) {
  assert(!browser_thread);
  assert(strcmp(target, "#canvas") == 0);
  *width = actual_width; *height = actual_height;
  return 0;
}
CALLBACKS
int main(void) {
  double dpr = 2.0;
  int width, height;
  platform_emscripten_update_canvas_dimensions_cb(1280, 960, &dpr);
  assert(mutations == 0 && actual_width == 64);
  assert(data.canvas_width == 1280 && data.canvas_height == 960 && data.device_pixel_ratio == 2.0);
  browser_thread = 0;
  platform_emscripten_get_canvas_size(&width, &height);
  assert(width == 1280 && height == 960 && actual_width == width && actual_height == height);
  assert(mutations == 1);
  platform_emscripten_get_canvas_size(&width, &height);
  assert(mutations == 1 && "unchanged dimensions must not reset the canvas");
  browser_thread = 1;
  platform_emscripten_update_canvas_dimensions_cb(1920, 1080, &dpr);
  assert(mutations == 1);
  browser_thread = 0;
  platform_emscripten_get_canvas_size(&width, &height);
  assert(width == 1920 && height == 1080 && mutations == 2);
  browser_thread = 1;
  platform_emscripten_update_canvas_dimensions_cb(0, 0, &dpr);
  assert(data.canvas_width == 1920 && data.canvas_height == 1080);
  emscripten_platform_data = NULL;
  platform_emscripten_update_canvas_dimensions_cb(10, 10, &dpr);
  assert(mutations == 2);
  return 0;
}
'''


class CanvasResizeTests(unittest.TestCase):
    def test_rejects_upstream_drift_and_reapplication(self):
        patch = patch_module().patch_platform
        with self.assertRaisesRegex(ValueError, "MKXP_CANVAS_RESIZE_SOURCE_INVALID"):
            patch(source().replace('emscripten_set_canvas_element_size("#canvas", width, height);', 'changed();'))
        with self.assertRaisesRegex(ValueError, "MKXP_CANVAS_RESIZE_SOURCE_INVALID"):
            patch(patch(source()))

    def test_both_graphics_drivers_poll_on_the_render_thread(self):
        for name in ("emscriptenegl_ctx.c", "emscriptenwebgl_ctx.c"):
            driver = (ROOT / "retroarch/gfx/drivers_context" / name).read_text(encoding="utf-8")
            self.assertIn("platform_emscripten_get_canvas_size(&input_width, &input_height);", driver)
        recipe = (RECIPE / "build-web.sh").read_text(encoding="utf-8")
        self.assertIn('python3 "$source_root/.github/rpg-runtime/patch-canvas-resize.py"', recipe)

    def test_browser_reports_and_render_thread_applies_only_changed_positive_sizes(self):
        patched = patch_module().patch_platform(source())
        callbacks = "\n".join(function(patched, signature) for signature in (
            "void platform_emscripten_update_canvas_dimensions_cb(",
            "void platform_emscripten_get_canvas_size(",
        ))
        with tempfile.TemporaryDirectory() as directory:
            c_file = Path(directory) / "canvas.c"
            output = Path(directory) / "canvas"
            c_file.write_text(HARNESS.replace("CALLBACKS", callbacks), encoding="utf-8")
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", str(c_file), "-o", str(output)],
                           check=True, capture_output=True)
            result = subprocess.run([str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
