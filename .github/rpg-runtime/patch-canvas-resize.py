#!/usr/bin/env python3
"""Keep browser size observations separate from render-thread canvas mutations."""

from __future__ import annotations

import argparse
from pathlib import Path


def patch_platform(source: str) -> str:
    old_callback = '''   printf("[INFO] Setting real canvas size: %d x %d\\n", width, height);
   emscripten_set_canvas_element_size("#canvas", width, height);
   if (!emscripten_platform_data)
      return;
   PLATFORM_SETVAL(u32, &emscripten_platform_data->canvas_width,        width);'''
    new_callback = '''   /* Browser callbacks only publish dimensions. Mutating the transferred
    * canvas here can synchronously proxy back to a worker waiting for the
    * browser, and changes layout during ResizeObserver notification delivery. */
   if (!emscripten_platform_data || width <= 0 || height <= 0 || !dpr)
      return;
   PLATFORM_SETVAL(u32, &emscripten_platform_data->canvas_width,        width);'''
    old_getter = '''void platform_emscripten_get_canvas_size(int *width, int *height)
{
   *width  = PLATFORM_GETVAL(u32, &emscripten_platform_data->canvas_width);
   *height = PLATFORM_GETVAL(u32, &emscripten_platform_data->canvas_height);

   if (*width != 0 || *height != 0)
      return;

   *width  = 800;
   *height = 600;
   RARCH_ERR("[EMSCRIPTEN] Could not get screen dimensions.\\n");
}'''
    new_getter = '''void platform_emscripten_get_canvas_size(int *width, int *height)
{
   int current_width = 0;
   int current_height = 0;
   *width  = PLATFORM_GETVAL(u32, &emscripten_platform_data->canvas_width);
   *height = PLATFORM_GETVAL(u32, &emscripten_platform_data->canvas_height);

   if (*width == 0 || *height == 0)
   {
      *width  = 800;
      *height = 600;
      RARCH_ERR("[EMSCRIPTEN] Could not get screen dimensions.\\n");
      return;
   }

   /* Called by the graphics driver's window check on the canvas-owning thread.
    * Avoid redundant mutations: assigning an unchanged size still resets canvas. */
   if (emscripten_get_canvas_element_size("#canvas", &current_width, &current_height)
         == EMSCRIPTEN_RESULT_SUCCESS &&
         (current_width != *width || current_height != *height))
      emscripten_set_canvas_element_size("#canvas", *width, *height);
}'''
    for old, new in ((old_callback, new_callback), (old_getter, new_getter)):
        if source.count(old) != 1 or new in source:
            raise ValueError("MKXP_CANVAS_RESIZE_SOURCE_INVALID")
        source = source.replace(old, new)
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    path = args.source / "retroarch/frontend/drivers/platform_emscripten.c"
    path.write_text(patch_platform(path.read_text(encoding="utf-8")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
