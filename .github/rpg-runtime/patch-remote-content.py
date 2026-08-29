#!/usr/bin/env python3
"""Make RetroArch FetchFS strict and configurable for remote game content."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Callable


EMSCRIPTEN_FETCHFS_4_0_8_SHA256 = (
    "1065a11fb336e75b9e0164ca7058bf9d417da0d7463b40a0c8e67a770088678e"
)

OLD_FETCH_DECLARATIONS = """   char *fetch_manifest = getenv(\"FETCH_MANIFEST\");
   char *fetch_base_dir = getenv(\"FETCH_BASE_DIR\");"""
NEW_FETCH_DECLARATIONS = """   char *fetch_manifest = getenv(\"FETCH_MANIFEST\");
   char *fetch_base_dir = getenv(\"FETCH_BASE_DIR\");
   char *fetch_chunk_size_text = getenv(\"FETCH_CHUNK_SIZE_BYTES\");
   unsigned long fetch_chunk_size = 0;"""

OLD_FETCH_GUARD = """   if (fetch_manifest || fetch_base_dir)
   {
      /* fetch_manifest should be a path to a manifest file."""
NEW_FETCH_GUARD = """   if (fetch_manifest || fetch_base_dir || fetch_chunk_size_text)
   {
      char *fetch_chunk_size_end = NULL;
      errno = 0;
      fetch_chunk_size = strtoul(fetch_chunk_size_text ? fetch_chunk_size_text : \"\", &fetch_chunk_size_end, 10);
      if (!(fetch_manifest && fetch_base_dir && fetch_chunk_size_text) ||
          errno != 0 || !fetch_chunk_size_end || *fetch_chunk_size_end != '\\0' ||
          fetch_chunk_size < 64 * 1024 || fetch_chunk_size > 4 * 1024 * 1024 ||
          (fetch_chunk_size & (fetch_chunk_size - 1)) != 0)
      {
         printf(\"[FetchFS] FETCH_MANIFEST, FETCH_BASE_DIR, and a power-of-two FETCH_CHUNK_SIZE_BYTES from 65536 to 4194304 are required\\n\");
         abort();
      }
      /* fetch_manifest should be a path to a manifest file."""

OLD_FETCH_REQUIREMENTS = """      if (!(fetch_manifest && fetch_base_dir))
      {
         printf(\"[FetchFS] must specify both FETCH_MANIFEST and FETCH_BASE_DIR\\n\");
         abort();
      }
"""

OLD_BACKEND = "fetch = wasmfs_create_fetch_backend(base_url, 16*1024*1024);"
NEW_BACKEND = "fetch = wasmfs_create_fetch_backend(base_url, (int)fetch_chunk_size);"

OLD_BASE_URL_TERMINATION = """         base_url[strcspn(base_url, "\\r\\n")] = '\\0'; // drop newline
         base_url[len-1] = '\\0'; // drop newline"""
NEW_BASE_URL_TERMINATION = """         base_url[strcspn(base_url, "\\r\\n")] = '\\0'; // terminate at the actual newline"""

OLD_HEAD = """        if (fileInfo.ok &&
            fileInfo.headers.has('Content-Length') &&
            fileInfo.headers.get('Accept-Ranges') == 'bytes' &&
            (parseInt(fileInfo.headers.get('Content-Length'), 10) > chunkSize*2)) {
          var size = parseInt(fileInfo.headers.get('Content-Length'), 10);
          wasmFS$JSMemoryRanges[file] = {
            size,
            chunks: [],
            chunkSize: chunkSize
          };
          len = Math.min(len, size-offset);
        } else {
          // may as well/forced to download the whole file
          var wholeFileReq = await fetch(url);
          if (!wholeFileReq.ok) {
            throw wholeFileReq;
          }
          var wholeFileData = new Uint8Array(await wholeFileReq.arrayBuffer());
          var text = new TextDecoder().decode(wholeFileData);
          wasmFS$JSMemoryRanges[file] = {
            size: wholeFileData.byteLength,
            chunks: [wholeFileData],
            chunkSize: wholeFileData.byteLength
          };
          return Promise.resolve();
        }"""

NEW_HEAD = """        var contentLength = fileInfo.headers.get('Content-Length');
        var size = Number(contentLength);
        if (!fileInfo.ok ||
            fileInfo.headers.get('Accept-Ranges') != 'bytes' ||
            !contentLength || !/^[1-9][0-9]*$/.test(contentLength) ||
            !Number.isSafeInteger(size)) {
          throw {status: 502, code: 'FETCHFS_RANGE_REQUIRED'};
        }
        wasmFS$JSMemoryRanges[file] = {
          size,
          chunks: [],
          chunkSize: chunkSize
        };
        len = Math.min(len, size-offset);"""

OLD_RANGE = """      var end = (lastChunk+1) * chunkSize;
      var response = await fetch(url, {headers:{'Range': `bytes=${start}-${end-1}`}});
      if (!response.ok) {
        throw response;
      }
      var bytes = await response['bytes']();"""

NEW_RANGE = """      var end = Math.min((lastChunk+1) * chunkSize, wasmFS$JSMemoryRanges[file].size);
      var response = await fetch(url, {headers:{'Range': `bytes=${start}-${end-1}`}});
      var expectedContentRange = `bytes ${start}-${end-1}/${wasmFS$JSMemoryRanges[file].size}`;
      if (response.status !== 206 ||
          response.headers.get('Content-Range') !== expectedContentRange) {
        throw {status: 502, code: 'FETCHFS_RANGE_PROTOCOL_INVALID'};
      }
      var bytes = await response['bytes']();
      if (bytes.byteLength !== end-start) {
        throw {status: 502, code: 'FETCHFS_RANGE_LENGTH_INVALID'};
      }"""


def replace_exact(source: str, old: str, new: str, code: str) -> str:
    if source.count(old) != 1 or (new and new in source):
        raise ValueError(code)
    return source.replace(old, new)


def patch_retroarch(source: str) -> str:
    source = replace_exact(
        source,
        OLD_FETCH_DECLARATIONS,
        NEW_FETCH_DECLARATIONS,
        "RPG_RUNTIME_FETCHFS_DECLARATIONS_INVALID",
    )
    source = replace_exact(
        source,
        OLD_FETCH_GUARD,
        NEW_FETCH_GUARD,
        "RPG_RUNTIME_FETCHFS_GUARD_INVALID",
    )
    source = replace_exact(
        source,
        OLD_FETCH_REQUIREMENTS,
        "",
        "RPG_RUNTIME_FETCHFS_REQUIREMENTS_INVALID",
    )
    source = replace_exact(
        source,
        OLD_BACKEND,
        NEW_BACKEND,
        "RPG_RUNTIME_FETCHFS_BACKEND_INVALID",
    )
    return replace_exact(
        source,
        OLD_BASE_URL_TERMINATION,
        NEW_BASE_URL_TERMINATION,
        "RPG_RUNTIME_FETCHFS_BASE_URL_TERMINATION_INVALID",
    )


def patch_emscripten(source: str) -> str:
    source = replace_exact(
        source,
        OLD_HEAD,
        NEW_HEAD,
        "RPG_RUNTIME_FETCHFS_HEAD_INVALID",
    )
    return replace_exact(
        source,
        OLD_RANGE,
        NEW_RANGE,
        "RPG_RUNTIME_FETCHFS_RANGE_INVALID",
    )


def write_patched(path: Path, patcher: Callable[[str], str]) -> None:
    source = path.read_text(encoding="utf-8")
    patched = patcher(source)
    path.write_text(patched, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--emscripten-root", type=Path, required=True)
    args = parser.parse_args()

    fetchfs = args.emscripten_root / "src/lib/libwasmfs_fetch.js"
    if hashlib.sha256(fetchfs.read_bytes()).hexdigest() != EMSCRIPTEN_FETCHFS_4_0_8_SHA256:
        raise SystemExit("RPG_RUNTIME_EMSCRIPTEN_FETCHFS_SOURCE_INVALID")

    try:
        write_patched(
            args.source / "retroarch/frontend/drivers/platform_emscripten.c",
            patch_retroarch,
        )
        write_patched(fetchfs, patch_emscripten)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
