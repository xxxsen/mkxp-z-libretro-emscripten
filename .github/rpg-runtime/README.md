# RPG Runtime mkxp-z Web release

Tags matching `retrom-core-f2efc98-rN` build only the pinned mkxp-z core and
RetroArch Emscripten frontend. The workflow never downloads or packages RPG
Maker games or RTP archives.

The release contains:

- `mkxp-z_libretro.js`
- `mkxp-z_libretro.wasm`
- `rpg-runtime-release.json`

Before a tag exists, a maintainer can dispatch the same workflow on a
`feat/*`, `fix/*`, `build/*`, or active `retrom/*` branch. It uploads the JS
and Wasm pair as a seven-day integration artifact without creating a Release.
That candidate is intended for the aggregate runtime's local asset override
and Retrom product-chain validation. Only a tag run validates release metadata
and creates the immutable GitHub Release.

The tagged superproject fixes the exact mkxp-z and RetroArch gitlinks. A small
build patch replaces mkxp-z's random sandbox function-type identifiers with
identifiers derived from the function type name. This is required because the
sandbox binding hash is part of the save-state compatibility contract.
The release preparation also guards the post-state-load movie-frame query
against the transient empty sandbox state observed after a successful
libretro `retro_unserialize`; without the guard the next frame aborts before
restored game input can resume.

The browser can read `Module._runtime_get_frame_count()` and
`Module._runtime_get_restore_result()` from the main thread without invoking
RetroArch GL commands. Both read atomics maintained by the core thread. Frame
count advances only for presented game-core frames, never RetroArch's dummy
core after a failed content load; restore result is zero while
pending, one after successful deserialization, and minus one on failure.
Frames alone never imply restore success. These observations require no
preload script, map position, fixture variable, or host-provided proof.
They do not alter the mkxp sandbox bindings or the checkpoint format.

`Module._runtime_request_exit()` publishes an atomic shutdown request. The core
loop consumes it before visibility, pause or graphics checks and runs the normal
RetroArch `main_exit` path. This unloads the game, stops audio and releases browser
observers before Emscripten executes C++ global destructors and terminates workers.
Hosts wait for `Module.onExit` before removing the canvas; they must not directly
force-exit a running threaded core. Native regressions cover coalescing requests
and the core-loop boundary. No host route, game data or keyboard binding is part
of this private lifecycle ABI.

Browser resize observations publish positive dimensions and pixel ratio through
the platform atomics only. The graphics driver's window check applies changed
dimensions on the canvas-owning render thread. This avoids mutating layout in
ResizeObserver delivery or synchronously proxying canvas changes across threads;
unchanged dimensions never reset the drawing buffer. A native C regression runs
the patched upstream callbacks with explicit browser/render ownership.

Explicit local builds retain verified stage-one/core artifacts and Meson source
archives under this worktree's ignored `.cache/rpg-runtime-build/`. A stage-one
cache hit requires identical MKXP source, relevant stage recipe and toolchain bytes and a matching
artifact manifest; corrupt cached bytes fail closed. Later-stage failures do
not remove this cache. GNU archives are prefetched from the GNU origin with
the SHA-256 declared by the locked wrap file, avoiding mirror timeouts.
The pinned Meson version uses its standard
[package cache](https://mesonbuild.com/Wrap-dependency-system-manual.html)
for other source archives. Cache reuse never skips release verification.

The generated Ruby sandbox translation units use per-file release optimization,
not whole-program LTO; the MKXP core and other dependencies retain LTO. Core
compilation uses two jobs, wasm-ld one worker, and Binaryen two workers. This
avoids combining the large Ruby program into one memory-intensive LTO module,
without changing the threaded runtime ABI or save format. Core artifacts are
verified and cached before linking; a frontend-only change does not rebuild them.

Remote `.mkxpz` project and RTP archives are exposed through RetroArch's
WasmFS FetchFS backend. The Retrom build makes that backend fail closed: the
host must provide a bounded power-of-two chunk size, the remote endpoint must
advertise byte ranges, and every read must return an exact `206` response with
the expected `Content-Range` and byte length. It never falls back to a whole
archive download. The host remains responsible for creating the FetchFS
manifest and for passing content URLs; this fork does not know any Retrom API
or launch identifier.

The pinned FetchFS URL join is corrected at the base/path boundary: directory
paths already start with a slash, so appending another slash would request a
different URL. Escaped paths and query strings are preserved. The frontend
build clears only its ephemeral container's Emscripten system-library cache
after patching, ensuring a precompiled WasmFS cannot bypass this correction.

Metadata digests describe the uploaded bytes for cache diagnostics. A consumer
identifies the runtime by repository, tag, tag commit, asset filenames and
`mkxp-state`; observed digests are not release identity.
