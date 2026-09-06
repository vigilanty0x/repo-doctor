# Public environment examples and declared keys

`builtin.env-example` is registered once in the existing `secrets` category.
It uses the existing Scanner observations and native findings, remediation,
renderers and workflow receipt. It does not open files, execute target code,
load a plugin, inspect a process environment or start another scanner/store.

Only three exact, case-sensitive basenames are eligible: `.env.example`, the
canonical public manifest `env-keys.json`, and its legacy alias `.env.keys.json`.
Each directory is a separate scope. No cross-project merge,
parent inheritance or automatic discovery of “actual” configuration is made.

## Public input contract

The optional sibling manifest is exactly:

```json
{"schema":"repo-doctor/env-keys-v1","keys":["APP_MODE","API_KEY"]}
```

New examples use `env-keys.json`, a public name that does not resemble private
environment configuration. The legacy filename remains accepted. When both
names are observed, both must be valid and declare the same set of names;
ordering and whitespace may differ. A malformed or conflicting alias is a rule
error, never silently ignored or merged. The canonical manifest supplies the
finding digest when both agree. Both observations consume the existing shared
byte budget. No other configuration filename becomes eligible.

It declares expected key names, not values and not an observed loaded
environment. Duplicate JSON keys, unknown fields/schema, non-finite values,
non-list keys, duplicates and invalid names are refused. Names must match
`[A-Z][A-Z0-9_]{0,127}`. A caller cannot disable sensitive-name/value policy by
emptying this list or supplying extra policy fields.

The example uses the historical simple `KEY=value` grammar. Blank lines and
whole-line comments are ignored. Keys must be unique and uppercase, with no
whitespace around the equals sign's left side. There is no shell expansion,
`export`, quoting, interpolation, multiline value or inline-comment semantics.
Quotes are ordinary value characters: use `API_KEY=` rather than `API_KEY=""`
for an empty placeholder under this contract. Accepted sensitive placeholders
are empty, `<replace-me>`, `<required>`, `changeme`, `replace-me`, `example`,
compared case-insensitively. This is policy parity, not a credential-validity
check. The observed text's surrounding line whitespace follows the original
parser's stripping behavior.

## Findings and incomplete observations

| Code | Level / classification | Meaning |
| --- | --- | --- |
| `ENV_EXAMPLE_SECRET_VALUE` | high / proof | Sensitive key has a non-placeholder value, or a known provider-shaped value appears under any key |
| `ENV_EXAMPLE_KEY_MISSING` | high / proof | Declared key is absent from the observed sibling example |
| `ENV_EXAMPLE_KEY_EXTRA` | high / proof | Observed example key is absent from the declared sibling list |
| `ENV_EXAMPLE_KEYS_UNMEASURED` | low / inference | No declared key manifest was observed; only placeholder/value policy was checked |

“Proof” here refers to those local text/policy facts, never proof of an active
credential or production configuration. The existing generic secret scanner
is unchanged and may emit its own finding for the same text. No previous
finding is hidden or deduplicated across different diagnostic codes.

Each finding contains only a safe key name, relative path/line and SHA-256 of
the observed example/manifests. Values are never emitted, including malformed
input and parser exceptions. The hashes describe Scanner-decoded UTF-8 text,
not a signed or immutable byte snapshot. Replacement characters are refused
to avoid treating undecodable content as a healthy example.

An example without a manifest still receives the non-disableable sensitive
policy and the explicit unmeasured finding. Existing severity thresholds are
unchanged: `--fail-on low` blocks the missing parity; `--fail-on high` can
permit that low inference, which must not be presented as measured key parity.

A manifest without an observed example, unread/oversized/binary input, invalid
syntax, duplicate observation, empty/inconclusive scope or exceeded budget
raises a rule error. The normal workflow becomes `FAILED`, `gate_passed=false`,
even with `fail_on=none`. An excluded or symlinked example is not guessed to be
an empty readable file. No supported content means no rule success claim.

Bounds: 128 directories, 1,000,000 bytes per example, 256 KiB per manifest,
8 MiB total text, 10,000 keys per map. The native Scanner/RuleRegistry limits
remain active; cooperative deadline checks run between lines, keys and findings.
POSIX's existing main-thread timer remains unchanged. There is no guarantee
that a long single Python primitive can be preempted on Windows.

## Protect actual environment files

The generic Scanner's existing default does not exclude `.env`. The new rule
does not expand that read boundary: it only receives the three exact names above.
For actual audits, use the existing `exclude` configuration to exclude real
environment files. In particular, the exact exclusion `.env` still admits
`.env.example`, `env-keys.json` and `.env.keys.json`. Add other actual environment filenames to
the same explicit exclusion list where relevant; no new glob semantics are
introduced by this lot.

The reproducible example uses a configuration preserving default exclusions
and adding `.env`:

```text
repo-doctor run examples/env-example --config examples/env-secrets-only.json --output /new/private/report --fail-on high
repo-doctor rules --format json
repo-doctor explain ENV_EXAMPLE_SECRET_VALUE
```

The shipped example is synthetic, contains placeholders only and matches its
declared keys. The output directory must be new and outside the audited tree.
Its legacy key file is retained for source compatibility/history, but the active
distribution uses `env-keys.json`; deployment secret exclusions are unchanged.
The equivalent Python API is the existing `run_workflow(..., config=Config(...))`.
`compare_example(declared_keys, example_text)` is a pure helper; its inputs are
caller declarations and never trigger reads of a process environment.

## Source parity and remaining CONS‑11 scope

The policy/parser originates from env-example-guard commit
`4df3eb9ae1347c5f03618b78e2a5a33507750c75` (Apache-2.0). Its exact
`core.py` SHA-256 is
`ae6effa36178ceeafbe622094a5b979d9d389e825f0c5be723c6ea6a25823ee2`.
The retained source is a test oracle, never a runtime import. Tests compare
the actual original `check()` result on 105 cases. Additional checks enforce
Scanner budgets, safe output, native workflow admission and gate behavior.
The pure helper does not expose the historical optional `secret_keys` input;
baseline policy is always present. Invalid key types and decoded replacement
characters are rejected more strictly by this adapter.

This tranche does not integrate arbitrary schema checking, dependency graphs,
SQLite diagnostics or migrations. It does not replace secrets-hygiene or claim
complete secret detection. Exact npm lock drift remains covered by the earlier
native dependency rule. Receipt schema and unrelated source modules remain
unchanged.
