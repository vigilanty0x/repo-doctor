# npm declarations and lock-recorded versions

The existing Scanner now calls `builtin.dependency-lock-drift`, explicitly
registered in `build_default_registry()` under category `dependencies`. It uses
the same confined file observations as the other rules. No additional reader,
package manager, installed environment, plugin discovery or network access is
introduced. The integrated `run`, `scan`, `rules`, `explain`, remediation, report
renderers and baseline workflow consume the normal findings.

## Supported observation

A pair consists of actual Scanner observations of neighboring `package.json`
and `package-lock.json`, with exact filenames. The latter must record
`lockfileVersion` 2 or 3 and a `packages` object. For each direct dependency or
dev dependency with an exact supported version, the rule compares its declaration
to `packages["node_modules/NAME"].version`. Scoped package names and independent
nested projects with their own sibling lock work in the same way. Transitive
extras do not count as undeclared direct dependencies.

An exact changed version emits `DEPENDENCY_LOCK_DRIFT`; a missing direct entry
in an observed packages object emits `DEPENDENCY_LOCK_ENTRY_MISSING`. Both are
high-severity facts about the text read, not a claim that a dependency is
vulnerable or that this lock is the environment actually installed. Empty
observed packages maps are real observations of missing entries, never a
substitute for missing or unread lock content.

Supported version syntax has three non-negative decimal components without
leading zeroes, with optional prerelease/build strings. Comparisons are exact
and do not run npm/semver resolution. A leading `v`, range, alias, URL or
workspace constraint is outside this comparison scope. The rule does not
validate the whole npm lock specification or its integrity fields.

## Incomplete and unknown cases

`DEPENDENCY_LOCK_UNMEASURED` records a fixed reason for:

- package-lock absent from observations, or a sibling npm-shrinkwrap present;
- unsupported lock version, package-name shape or recorded version;
- non-exact declaration, workspace/alias/URL, linked package;
- conflicting declarations across direct scopes, overlap with optional scope,
  or overrides that would require resolution semantics.

Optional-only and peer-only dependencies, workspace root-lock discovery, pnpm,
yarn, lock v1, installed packages and vulnerability assessment are outside this
lot. No finding for such an unrequested surface proves its correctness.
Nonempty overrides conservatively make the whole manifest unmeasured.

The unmeasured finding is a **low-severity inference**. It can coexist with a
completed audit and a passing high-severity threshold. Require `--fail-on low`
when unknown comparisons must refuse the quality gate. Do not display such a
finding as verified version agreement. This preserves the existing distinction
between audit completion and repository quality policy.

Malformed or duplicate-key JSON, non-finite constants, unread supported content,
invalid supported map/entry shape and map-budget overflow fail rule execution.
The CLI returns 2; `run` writes a FAILED result with `gate_passed=false`, even
with `--fail-on none`. Timeout and finding limits keep their existing blocked
states. Invalid source data never becomes an empty healthy lock map.

## Bounds and confidentiality

Existing file, global-byte and time budgets apply before rules execute. Each
declared/recorded comparison has at most 2000 entries per map and 65536 bytes of
canonical JSON. Names and versions are bounded at 200 characters; adapter names
and versions use a restricted syntax. The pure map comparator rejects control
characters, nonstring inputs and implicit empty maps. It accepts known empty
maps only through the explicit `allow_empty=True` extension.

Evidence retains a sanitized dependency name, fixed mode/reason, and SHA-256
digests of observed manifest text, lock text and relevant version strings. It
does not retain version values, scripts, resolved URLs, credentials, lockfile
contents or complete source. Existing final sanitizers remain active in every
report renderer. Paths can reveal project names and should be handled as before.
Text hashes are computed once per observed file; version hashes are computed
per difference. The Scanner decodes text with replacement, so these are text
observation hashes, not an assertion of original raw-byte identity.

The finding fingerprint binds code, path, line and evidence using the existing
contract. Editing either observed file therefore invalidates a previous
suppression, even if the same dependency differs. This avoids reusing an old
suppression as authority for new source text. Whole-directory immutability is
not claimed by `run`; use a frozen checkout when needed.

## Source parity

The independent oracle is `dependency-drift-reporter` at commit
`5af035db71c6cbd0c3f168929714a6d49994526b`, core blob
`d35b3ec53becde100115177a0c580399a0f5e159`, SHA-256
`7a0ead0beb9a0150e4352d41966847c52736e744d311ed1c1ee11ed678f1ff90`.
The exact source is retained only under `tests/source_oracles/`, with its
Apache-2.0 provenance. Production does not import it.

The source compares supplied maps called `manifest` and `installed`; it does
not itself observe an installed environment. The native comparator preserves
the sorted union, missing values and exact comparison over their common finite
domain, while naming the second side **recorded**. Tests compare 103 positive,
negative and deterministic varied maps against that real source. The adapter
then obtains its maps from actual confined Scanner observations. This proves
the scoped comparison and caller, not consolidation of every historical source.

## Example

```sh
repo-doctor run examples/lock-drift --config examples/dependencies-only.json --output lock-assessment --fail-on high
repo-doctor explain DEPENDENCY_LOCK_DRIFT
```

The example deliberately exits 1 and writes a false quality gate. It records
one high finding and one remediation item. Reusing the output directory is
refused. To verify the opposite case, create a separate synthetic copy and make
the declared and recorded versions equal; never rewrite an existing assessment
as a way of claiming a different result.

The root project tests, the real CLI and workflow, deterministic/source parity,
output digests, redaction, registry limits, file links and private-process
regressions are exercised by this lot's proof package. A development wheel can
be loaded directly without installation; that does not replace the existing
pinned release build and install matrix.
