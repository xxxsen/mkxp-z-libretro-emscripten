#!/usr/bin/env python3
"""Expose actual threaded-core presentation and state-load completion."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def replace_exact(source: str, old: str, new: str) -> str:
    if source.count(old) != 1 or new in source:
        raise ValueError("MKXP_RUNTIME_STATUS_SOURCE_INVALID")
    return source.replace(old, new)


def guarded(code: str) -> str:
    return "#ifdef EMSCRIPTEN\n" + code + "\n#endif\n"


def patch_save(source: str) -> str:
    source = replace_exact(
        source, '#include "tasks_internal.h"\n',
        '#include "tasks_internal.h"\n' +
        guarded('#include "../frontend/drivers/runtime-status.h"'),
    )
    if source.count("ret = content_deserialize_state(buf, _len);") != 1:
        raise ValueError("MKXP_RUNTIME_STATUS_SOURCE_INVALID")
    source = replace_exact(
        source,
        "   if (!ret)\n      goto error;\n\n   free(buf);\n   free(load_data);",
        "   if (!ret)\n      goto error;\n\n" +
        "   free(buf);\n   free(load_data);\n" +
        guarded("   runtime_state_finished(true);"),
    )
    source = replace_exact(
        source,
        'error:\n   RARCH_ERR("[State] %s \\"%s\\".\\n",',
        "error:\n" + guarded(
            "   if (!(load_data->flags & SAVE_TASK_FLAG_LOAD_TO_BACKUP_BUFF))\n"
            "      runtime_state_finished(false);"
        ) + '   RARCH_ERR("[State] %s \\"%s\\".\\n",',
    )
    head, request = source.split("bool content_load_state(const char *path,", 1)
    request, tail = request.split("bool content_rename_state(", 1)
    request = replace_exact(
        request,
        "error:\n   if (state)\n      free(state);\n   if (task)\n",
        "error:\n" + guarded(
            "   if (!load_to_backup_buffer) runtime_state_finished(false);"
        ) + "   if (state)\n      free(state);\n   if (task)\n",
    )
    source = head + "bool content_load_state(const char *path," + request + "bool content_rename_state(" + tail
    return patch_blocking_save(source)


def patch_blocking_save(source: str) -> str:
    head, save = source.split("bool content_auto_save_state(const char *path)", 1)
    save, tail = save.split("/**\n * content_save_state:", 1)
    save = replace_exact(save,
        "   if (_len != (size_t)intfstream_write(file, serial_data, _len))",
        "   /* WasmFS uses a vector. Reserve the exact raw RASTATE size before\n"
        "    * libc splits writes: a power-of-two payload plus its envelope\n"
        "    * otherwise doubles capacity on the final flush. */\n"
        "   if (\n#ifdef EMSCRIPTEN\n"
        "       (!settings->bools.savestate_file_compression &&\n"
        "        intfstream_truncate(file, _len) != 0) ||\n#endif\n"
        "       _len != (size_t)intfstream_write(file, serial_data, _len))")
    save = replace_exact(save,
        "   intfstream_close(file);\n   free(serial_data);\n   free(file);",
        "   bool closed = intfstream_close(file) == 0;\n   free(serial_data);\n   free(file);")
    save = replace_exact(save, "   return true;", "   return closed;")
    return head + "bool content_auto_save_state(const char *path)" + save + "/**\n * content_save_state:" + tail


def patch_video(source: str) -> str:
    source = replace_exact(
        source, '#include "video_driver.h"\n',
        '#include "video_driver.h"\n' +
        guarded('#include "../frontend/drivers/runtime-status.h"'),
    )
    return replace_exact(
        source, "   video_st->frame_count++;\n",
        "   video_st->frame_count++;\n" + guarded(
            "   if (render_frame && data && (video_st->flags & VIDEO_FLAG_ACTIVE) &&\n"
            "       runloop_st->current_core_type == CORE_TYPE_PLAIN)\n"
            "      runtime_frame_presented();"
        ),
    )


def patch_linker(source: str) -> str:
    if "RETROM_BOUNDED_LINKER" in source or "$(LDFLAGS)" not in source:
        raise ValueError("MKXP_RUNTIME_STATUS_SOURCE_INVALID")
    # Ruby creates a large LTO module. Bound link workers and LTO optimization
    # without dropping runtime/threading flags or O3 post-link optimization.
    return source + (
        "\n# RETROM_BOUNDED_LINKER\n"
        "LDFLAGS += -Wl,--threads=1,--lto-O2 --emit-symbol-map\n"
        "export BINARYEN_CORES=2\n"
    )


def patch_mainloop(source: str) -> str:
    return replace_exact(
        source, "void emscripten_mainloop(void)\n{\n",
        '#include "frontend/drivers/runtime-status.h"\n\n'
        "void emscripten_mainloop(void)\n{\n"
        "   /* Shutdown precedes visibility, pause, audio and graphics checks.\n"
        "    * main_exit unloads the core and unregisters browser observers on\n"
        "    * their owning threads before Emscripten runs global destructors. */\n"
        "   if (runtime_take_exit_request())\n"
        "   {\n"
        "      main_exit(NULL);\n"
        "      emscripten_force_exit(0);\n"
        "      return;\n"
        "   }\n"
        "   {\n"
        "      int request = runtime_take_state_request();\n"
        "      if (request)\n"
        "      {\n"
        "         char path[PATH_MAX_LENGTH];\n"
        "         if (!runloop_get_current_savestate_path(path, sizeof(path)))\n"
        "            runtime_state_finished(false);\n"
        "         else if (request == RUNTIME_STATE_SAVE)\n"
        "            /* Existing blocking writer: close/free before receipt. */\n"
        "            runtime_state_finished(content_auto_save_state(path));\n"
        "         else if (!command_event_main_state(CMD_EVENT_LOAD_STATE))\n"
        "            runtime_state_finished(false);\n"
        "      }\n"
        "   }\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    recipe = Path(__file__).resolve().parent
    frontend = args.source / "retroarch/frontend/drivers"
    for name in ("runtime-status.h", "runtime-status.c"):
        shutil.copyfile(recipe / name, frontend / name)
    for relative, patcher in (
        ("retroarch/tasks/task_save.c", patch_save),
        ("retroarch/gfx/video_driver.c", patch_video),
        ("retroarch/retroarch.c", patch_mainloop),
        ("retroarch/Makefile.emscripten", patch_linker),
    ):
        path = args.source / relative
        path.write_text(patcher(path.read_text(encoding="utf-8")), encoding="utf-8")
    platform = frontend / "platform_emscripten.c"
    source = platform.read_text(encoding="utf-8")
    if '"runtime-status.c"' in source:
        raise ValueError("MKXP_RUNTIME_STATUS_SOURCE_INVALID")
    platform.write_text(source + '\n#include "runtime-status.c"\n', encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
