# Retrom mkxp-z Web release

Tags matching `retrom-web-f2efc98-rN` build only the pinned mkxp-z core and
RetroArch Emscripten frontend. The workflow never downloads or packages RPG
Maker games or RTP archives.

The release contains:

- `mkxp-z_libretro.js`
- `mkxp-z_libretro.wasm`
- `retrom-runtime-release.json`

The tagged superproject fixes the exact mkxp-z and RetroArch gitlinks. A small
build patch replaces mkxp-z's random sandbox function-type identifiers with
identifiers derived from the function type name. This is required because the
sandbox binding hash is part of the save-state compatibility contract.

Metadata digests describe the uploaded bytes for cache diagnostics. Retrom
identifies the runtime by repository, tag, tag commit, asset filenames and
`mkxp-state-v1`; observed digests are not remote admission identity.
