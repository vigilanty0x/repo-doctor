# DevDocs

DevDocs is the public engineering-documentation suite for turning repository evidence into material a maintainer can actually use: onboarding, system maps, state views, event exploration, runbooks, postmortems, and generated documents.

The repository consolidates seven independently testable source tools while giving them one product boundary and one integration contract. The goal is not to hide the modules; it is to make their responsibilities non-overlapping and their handoffs explicit.

## One product, seven bounded modules

| Module | Role inside DevDocs |
|---|---|
| `codebase-onboarding-guide-generator` | Turn declared repository structure and commands into bounded onboarding notes |
| `system-map-generator` | Render a deterministic system/component map from structured inputs |
| `state-machine-visualizer` | Make explicit states and transitions inspectable |
| `event-log-explorer` | Explore bounded event records without changing their source |
| `runbook-builder` | Build operational procedures from declared steps and constraints |
| `failure-postmortem-kit` | Structure incident/failure evidence into a reproducible postmortem |
| `document-factory` | Produce deterministic final documents from validated structured content |

The recommended integration journey is:

`onboard → map → inspect state/events → build runbook → record failure evidence → publish document`

This is an **experience contract**, not an assertion that every module must be called in every workflow.

## Integration contract

[`DEVDOCS.json`](DEVDOCS.json) binds:

- the exact seven imported module identities;
- their audited source head/tree SHAs;
- `historyPreserved=true` and `treeMatch=true` for every import;
- merged public-governance commit `b5a99b401eb26deaad7b6aa144afed64f0db70b1`;
- canonical Portfolio Kit commit `0fc4b0dcf065d63c68556aea1bb25f86f1bab30d`;
- a fail-closed archive policy.

`python scripts/check_devdocs_integration.py` rejects missing/duplicate modules, changed import paths, malformed source SHAs, weakened history/tree evidence, integration-step drift, automatic archive, and missing rollback/human gates.

## Current state

**REHEARSAL / PREPARED integration.** The imported histories are preserved and the package matrix is tested, but this repository does not claim a stable DevDocs release yet.

A green consolidation PR is not enough to archive source repositories. Archive remains **BLOCKED** until release, compatibility, consumer inventory, redirect/transition handling, rollback, and explicit human approval all pass.

## CI boundary

Top-level CI owns integration verification only:

- exact DevDocs root contract and counter-proofs;
- explicit `ubuntu-24.04` runner;
- SHA-pinned external Actions;
- Python 3.11/3.12 wheel build/install verification for all seven imported packages;
- package-native tests and repository checks with the existing offline guard.

The integration layer does not silently rewrite module internals or weaken their individual contracts.

## Public boundary

Use synthetic public-safe fixtures in examples and tests. DevDocs documentation output can contain only what its explicit input contract allows; it must not invent verification, release, runtime, or adoption claims that are not present in the evidence.
