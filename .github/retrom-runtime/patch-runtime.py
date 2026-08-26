#!/usr/bin/env python3
"""Apply the reviewed Retrom state-restore lifecycle guard."""

from __future__ import annotations

import argparse
from pathlib import Path


OLD = (
    "    bool movie_dupe_frame = should_render && "
    "mkxp_retro::sandbox->get_movie_from_main_thread() != nullptr && "
    "Graphics::getMovieDupeFrame("
    "mkxp_retro::sandbox->get_movie_from_main_thread());"
)
NEW = OLD.replace(
    "should_render && mkxp_retro::sandbox->",
    "should_render && mkxp_retro::sandbox.has_value() && mkxp_retro::sandbox->",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    path = args.source / "mkxp-z/src/core.cpp"
    source = path.read_text(encoding="utf-8")
    if source.count(OLD) != 1 or NEW in source:
        raise SystemExit("RETROM_RUNTIME_RESTORE_GUARD_SOURCE_INVALID")
    path.write_text(source.replace(OLD, NEW), encoding="utf-8")
    if path.read_text(encoding="utf-8").count(NEW) != 1:
        raise SystemExit("RETROM_RUNTIME_RESTORE_GUARD_APPLY_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
