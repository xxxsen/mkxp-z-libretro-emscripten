# RPG Runtime mkxp-z Web release

Tags matching `rpg-runtime-f2efc98-rN` build only the pinned mkxp-z core and
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

Remote `.mkxpz` project and RTP archives are exposed through RetroArch's
WasmFS FetchFS backend. The Retrom build makes that backend fail closed: the
host must provide a bounded power-of-two chunk size, the remote endpoint must
advertise byte ranges, and every read must return an exact `206` response with
the expected `Content-Range` and byte length. It never falls back to a whole
archive download. The host remains responsible for creating the FetchFS
manifest and for passing content URLs; this fork does not know any Retrom API
or launch identifier.

Metadata digests describe the uploaded bytes for cache diagnostics. A consumer
identifies the runtime by repository, tag, tag commit, asset filenames and
`mkxp-state`; observed digests are not release identity.
