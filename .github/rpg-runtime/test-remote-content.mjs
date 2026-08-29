#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const sourcePath = process.argv[2];
if (!sourcePath) {throw new Error("patched FetchFS source path is required");}
const source = (await readFile(sourcePath, "utf8"))
  .replaceAll("{{{ cDefs.ENOENT }}}", "2")
  .replaceAll("{{{ cDefs.EBADF }}}", "9");

let library;
globalThis.addToLibrary = (value) => {library = value;};
globalThis.wasmFS$backends = [];
globalThis.wasmFS$JSMemoryRanges = {};
globalThis.__wasmfs_fetch_get_file_url = () => 1;
globalThis.__wasmfs_fetch_get_chunk_size = () => 65_536;
globalThis.UTF8ToString = () => "https://content.example/game.mkxpz";
globalThis.HEAPU8 = new Uint8Array(131_072);
globalThis.self = {location: {origin: "https://content.example"}};
vm.runInThisContext(source, {filename: sourcePath});
assert.ok(library);

function headers(values) {
  const normalized = new Map(Object.entries(values).map(([key, value]) => [key.toLowerCase(), value]));
  return {
    get: (name) => normalized.get(name.toLowerCase()) ?? null,
    has: (name) => normalized.has(name.toLowerCase()),
  };
}

function head() {
  return {ok: true, status: 200, headers: headers({"Accept-Ranges": "bytes", "Content-Length": "1048576"})};
}

function partial(overrides = {}) {
  const bytes = new Uint8Array(65_536).fill(7);
  return {
    ok: true,
    status: 206,
    headers: headers({"Content-Range": "bytes 0-65535/1048576"}),
    bytes: async () => bytes,
    ...overrides,
  };
}

async function runCase(rangeResponse) {
  globalThis.wasmFS$JSMemoryRanges = {};
  globalThis.wasmFS$backends = [];
  const requests = [];
  globalThis.fetch = async (_url, options = {}) => {
    requests.push(options);
    return options.method === "HEAD" ? head() : rangeResponse;
  };
  await library._wasmfs_create_fetch_backend_js(1);
  const result = await globalThis.wasmFS$backends[1].read(7, 0, 4, 0);
  return {requests, result};
}

const valid = await runCase(partial());
assert.equal(valid.result, 4);
assert.deepEqual(valid.requests.map((request) => request.method ?? "GET"), ["HEAD", "GET"]);
assert.equal(valid.requests[1].headers.Range, "bytes=0-65535");

const fullBody = await runCase(partial({status: 200}));
assert.equal(fullBody.result, -9);
assert.equal(fullBody.requests.length, 2, "must not issue an un-ranged fallback GET");

const wrongRange = await runCase(partial({headers: headers({"Content-Range": "bytes 1-65535/1048576"})}));
assert.equal(wrongRange.result, -9);

const shortBody = await runCase(partial({bytes: async () => new Uint8Array(32)}));
assert.equal(shortBody.result, -9);

process.stdout.write("remote-content: ok\n");
