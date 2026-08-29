# Retrom mkxp-z Web fork maintenance rules

This fork builds the mkxp-z/RetroArch browser core consumed by
`xxxsen/retrom-runtime`. It must remain independent of any Retrom host
application API, database, review workflow, credentials, or private game
content.

## Repository identity

- `main` is an unmodified, fast-forward-only mirror of `upstream/main`.
- `retrom/f2efc98` is the only active Retrom maintenance baseline and the
  repository default branch. Retrom patches and release tags originate there,
  never from `main`.
- `upstream` must point to
  `https://github.com/white-axe/mkxp-z-libretro-emscripten.git`.
- `retrom-fork.json` is the machine-readable wrapper, core, and RetroArch
  baseline. Every upstream without a release tag is fixed by a full commit.
- Updating `main` must only fast-forward it to `upstream/main`. Updating the
  fixed Retrom baseline requires a reviewed `sync/upstream-g<12-hex-commit>`
  branch and a new `retrom/<baseline>` branch; do not merge a moving upstream
  `main` into the fixed baseline.

## Branches and commits

- Use only short-lived `fix/<task>-<slug>`, `feat/<task>-<slug>`,
  `build/<task>-<slug>`, or `sync/upstream-<baseline>` branches.
- Branch names use lowercase ASCII and hyphens. Do not create branches named
  `temp`, `clean`, `final`, `runtime-clean`, or with an agent/user name.
- Create work branches from `retrom/f2efc98`, merge one logical change at a
  time back into that baseline, then delete the work branch. GitHub PRs must
  use squash merge (or a reviewed rebase/fast-forward), never a merge commit.
  Commit `bf5f525e864b162bea0789d46932e5f800b80076` is the one immutable
  historical checkpoint accepted after PR #2 was merged incorrectly; the
  release workflow rejects every merge commit after that checkpoint.
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
- Create annotated tags only from a clean commit already merged into
  `retrom/f2efc98`. The tagged superproject must retain the exact wrapper and
  gitlink commits recorded in `retrom-fork.json`.
- Tags and published assets are immutable: never move a tag, overwrite an
  asset, or create aliases such as `latest`, `stable`, or `current`.
- The tag workflow is the only supported way to build and upload release
  assets. Observed hashes diagnose local/cache corruption; repository, tag,
  tag commit, asset filename, and adapter ABI define release identity.

Before publishing, run the checks relevant to the changed wrapper/core/build
code and verify that `.github/rpg-runtime/verify-release.py` accepts the output.
Do not publish games, RTP, credentials, or host-specific code.

The Web runtime must retain standard gamepad input, checkpoint creation,
checkpoint restore in a fresh runtime instance, and strict seekable remote
content reads. Remote project/RTP access may use generic URL and file-system
primitives, but must not import or encode a Retrom host API. A Range-capable
release must fail closed on full-body fallback, malformed `Content-Range`, or
response-length drift; do not trade these functional guarantees for a silent
whole-archive download.
