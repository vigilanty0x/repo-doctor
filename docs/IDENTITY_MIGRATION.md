# Repo Doctor identity and compatibility migration

## Canonical product identity

The maintained product and repository are **Repo Doctor** at
`vigilanty0x/repo-doctor`. The public CLI remains `repo-doctor`.

The Python import migration is additive:

- canonical import: `repo_doctor`
- transition/legacy import: `repo_doctor_ai`
- canonical module CLI: `python -m repo_doctor`
- transition module CLI: `python -m repo_doctor_ai`
- installed CLI: `repo-doctor`

The canonical package re-exports the exact legacy public API and aliases public
submodules to the same module objects. This avoids duplicate `Scanner`, `Config`,
registry, finding, or report class identities during the transition.

## Distribution-name exception

The Python distribution remains `repo-doctor-ai` for the migration candidate.
The audited 0.3.0 source documents that the shorter `repo-doctor` PyPI name is
owned by an unrelated third-party project. Claiming or publishing that
third-party distribution name would create a registry collision rather than
resolve one.

Therefore repository/product/CLI/import identity converges on Repo Doctor while
the distribution-name exception remains explicit and machine-readable. Any
future distribution rename requires a separately verified available namespace,
a deprecation package/redirect plan, consumer inventory, rollback, and human
release approval.

## Source 0.3.0 port

Audited source repository: `vigilanty0x/repo-doctor-ai`.

- source merge commit: `2886565887920e221777153c5a68f344d79319a6`
- source root tree: `399f2c32a600c65ac5660541f2bfa258eac09b46`
- source package tree: `5c1c029bebb9a080d061aed6ebdcb05689a51160`
- source verification run: `32064296603`

The source 0.3.0 release candidate passed 115 source tests, compile/diff checks,
offline source/wheel/sdist build and install gates, payload parity, and an
Ubuntu/Windows Python 3.11/3.12 CI matrix before this port.

The target migration copies the changed 0.3.0 implementation/test/documentation
blobs by exact Git blob SHA, then adds only the canonical import compatibility
layer and migration evidence. The historical `repo_doctor_ai` implementation is
not rewritten for naming convenience.

## History gate

The source 0.3.0 merge commit was not reachable from the target repository at the
start of this migration. Exact source blobs and package contents can therefore be
ported without claiming that exact source commit ancestry is already preserved.
The history gate stays BLOCKED until the source commit itself is a reachable
ancestor of the final target branch and is independently verified.

## Consumer and rollback gates

Before redirect, alias removal, release replacement, or archive:

1. inventory public/default-branch, package-registry and explicitly known private
   consumers of `repo-doctor-ai` and `repo_doctor_ai`;
2. preserve `repo_doctor_ai` for at least the transition release;
3. prove `repo_doctor` and `repo_doctor_ai` return identical public objects and
   CLI behavior;
4. bind a rollback receipt to the final candidate SHA;
5. keep `vigilanty0x/repo-doctor-ai` available until release, redirect, consumer,
   rollback, history and human gates all pass.

Rollback is fail-safe: retain the legacy import/package and source repository,
remove only the additive `repo_doctor` compatibility package from the candidate,
restore the previous target metadata if necessary, and rerun the exact 0.3.0
source gate plus legacy CLI/import smoke tests.

No redirect, package publication, merge, archive, deletion, or alias removal is
authorized by this document.
