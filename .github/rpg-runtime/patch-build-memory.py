#!/usr/bin/env python3
"""Keep large generated Ruby translation units out of whole-program LTO."""

import argparse
from pathlib import Path


def patch_ruby(source: str) -> str:
    anchor = "            'ruby',\n"
    if source.count(anchor) != 1 or "override_options: ['b_lto=false']" in source:
        raise ValueError("MKXP_RUBY_BUILD_SOURCE_INVALID")
    # Per-file release optimization remains enabled. Only this generated
    # sandbox library opts out; the MKXP core and other dependencies keep LTO.
    return source.replace(anchor, anchor + "            override_options: ['b_lto=false'],\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    target = args.source / "mkxp-z/meson.build"
    target.write_text(patch_ruby(target.read_text(encoding="utf-8")), encoding="utf-8")
