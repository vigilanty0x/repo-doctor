# Changelog

All notable changes are documented here.

## [Unreleased]

## [0.2.0] - 2026-08-18

### Added

- Release-quality CI across Ubuntu, Windows, and macOS on CPython 3.11, 3.12, and 3.13.
- Exact pinned build toolchain, wheel plus source distribution verification, and clean installed-artifact smoke tests.
- Portable CLI proof covering valid manifests (exit 0), semantic validation diagnostics (exit 1), and malformed JSON (exit 2).
- SHA-256 candidate checksums, CycloneDX 1.6 SBOM, and explicit `PREPARED` release evidence.
- GitHub/Sigstore SLSA provenance generation followed by strict independent `gh attestation verify` policy checks.
- Explicit publication-disable policy, release state machine, migration guidance, and rollback to 0.1.0.
- Consolidated `ai-project-provenance-badge` history retained under `packages/` without archive authorization.

### Compatibility

- The manifest **format remains version 1.0**; package version 0.2.0 does not introduce a JSON schema-version break.
- Existing `aim init`, `aim validate`, `aim render`, `aim schema`, Python API, and validation exit classes remain available.

`0.2.0` is PREPARED, not published. No tag, GitHub Release, package publication, source-repository archive, or deletion is implied.

## [0.1.0] - 2026-08-15

### Added

- Version 1.0 JSON format and bundled JSON Schema.
- Dependency-free `aim` CLI with `init`, `validate`, `render`, and `schema` commands.
- Cross-reference, safe-path, file-existence, and secret-signature validation.
- Deterministic GitHub-flavored Markdown rendering.
- Self-describing manifest, specification, examples, tests, and CI.
