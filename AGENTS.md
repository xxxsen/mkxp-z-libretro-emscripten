# Retrom mkxp-z Web fork maintenance rules

This fork builds the mkxp-z/RetroArch browser core consumed by
`xxxsen/retrom-runtime`. It must remain independent of any Retrom host
application API, database, review workflow, credentials, or private game
content.

## Repository identity

- `main` is the only long-lived Retrom maintenance branch.
- `upstream` must point to
  `https://github.com/white-axe/mkxp-z-libretro-emscripten.git`.
- `retrom-fork.json` is the machine-readable wrapper, core, and RetroArch
  baseline. Every upstream without a release tag is fixed by a full commit.
- Do not use GitHub's automatic **Sync fork** action. Upstream updates require a
  reviewed `sync/upstream-g<12-hex-commit>` branch.

## Branches and commits

- Use only short-lived `fix/<task>-<slug>`, `feat/<task>-<slug>`,
  `build/<task>-<slug>`, or `sync/upstream-<baseline>` branches.
- Branch names use lowercase ASCII and hyphens. Do not create branches named
  `temp`, `clean`, `final`, `runtime-clean`, or with an agent/user name.
- Merge one logical change at a time into `main`, then delete its branch.
- Never force-push, move, or delete another contributor's branch. A one-time
  repository normalization must be explicitly authorized by the maintainer.
- Preserve downstream patches as small reviewable commits so an upstream sync
  can reapply or retire them independently.

## Releases

- The existing baseline keeps the historical tag stem
  `rpg-runtime-f2efc98-rN`. A future untagged upstream baseline uses
  `rpg-runtime-g<12-hex-commit>-rN`.
- `rN` increases for any source, build, asset, or adapter-contract change while
  the upstream baseline is unchanged. A new upstream baseline restarts at
  `r1`, with optional `-rc.N` only for integration candidates.
- Create annotated tags only from a clean commit already merged into `main`.
- Tags and published assets are immutable: never move a tag, overwrite an
  asset, or create aliases such as `latest`, `stable`, or `current`.
- The tag workflow is the only supported way to build and upload release
  assets. Observed hashes diagnose local/cache corruption; repository, tag,
  tag commit, asset filename, and adapter ABI define release identity.

Before publishing, run the checks relevant to the changed wrapper/core/build
code and verify that `.github/rpg-runtime/verify-release.py` accepts the output.
Do not publish games, RTP, credentials, or host-specific code.
