# AI Assistance Manifest

[![CI](https://github.com/vigilanty0x/ai-assistance-manifest/actions/workflows/ci.yml/badge.svg)](https://github.com/vigilanty0x/ai-assistance-manifest/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Manifest: 1.0](https://img.shields.io/badge/AI%20Manifest-1.0-6f42c1.svg)](AI_ASSISTANCE.json)

A small, deterministic standard and dependency-free Python CLI for declaring how humans and AI systems contributed to a software project.

**Package 0.2.0 is PREPARED, not published.** The manifest **format remains 1.0**. `release-policy.v1.json` keeps `publish_enabled=false`; normal CI cannot create `v0.2.0`, a GitHub Release, or a package publication. Rollback is 0.1.0. See [Migration to 0.2](MIGRATION-0.2.md) and [Release contract](docs/RELEASE.md).

It answers the questions that a vague “built with AI” badge does not:

- Which systems were used, and for which roles?
- What decisions remained human?
- What files or tasks were AI-assisted?
- Which claims have reproducible evidence?
- What is verified, inferred, blocked, or unknown?
- What limitations should a reviewer know?

The tool validates the declaration, cross-references models and evidence, rejects unsafe evidence paths, detects several common secret formats, and generates stable GitHub-flavored Markdown.

## Quick start

AI Assistance Manifest requires Python 3.11 or newer and has no runtime dependencies.

```bash
python -m pip install .
aim --version
aim init
aim validate AI_ASSISTANCE.json
aim render AI_ASSISTANCE.json --output AI_ASSISTANCE.md
```

For a stricter repository check:

```bash
aim validate AI_ASSISTANCE.json --check-files --root .
```

Machine-readable diagnostics are available for CI:

```bash
aim validate AI_ASSISTANCE.json --check-files --format json
```

The process exits with `0` for a valid manifest, `1` for validation findings, and `2` for input or usage errors. Flagship CI explicitly proves all three exit classes.

## Canonical files

- `AI_ASSISTANCE.json` is the source of truth.
- `AI_ASSISTANCE.md` is generated for human review.
- [`manifest.schema.json`](src/ai_assistance_manifest/schema/manifest.schema.json) supports editor and ecosystem integration.
- [`SPEC.md`](SPEC.md) defines the normative **manifest format 1.0** behavior.

Do not hand-edit the generated Markdown. Regenerate it after changing the JSON manifest.

## Minimal example

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "example-project",
    "owners": [{"name": "Maintainer", "role": "Final decision-maker"}]
  },
  "assistance": {
    "summary": "AI assisted with implementation; a human reviewed the result.",
    "autonomy": "collaborative",
    "human_review": {"required": true, "final_authority": "Maintainer"}
  },
  "models": [
    {"id": "assistant", "provider": "Example", "name": "Coding model", "roles": ["Implementation"]}
  ],
  "contributions": {
    "human": [
      {"actor": "Maintainer", "roles": ["Reviewer"], "decisions": ["Approved the final diff"]}
    ],
    "ai": [
      {
        "id": "build",
        "model_ref": "assistant",
        "tasks": ["Draft implementation"],
        "artifacts": ["src/example.py"],
        "evidence_refs": ["tests"],
        "reviewed_by": "Maintainer"
      }
    ]
  },
  "evidence": [
    {"id": "tests", "type": "test", "status": "verified", "location": "tests", "description": "Regression tests"}
  ],
  "limitations": ["This declaration is self-reported and does not prove authorship."]
}
```

Run `aim init` for a complete, diff-friendly template.

## Validation guarantees

Package 0.2.0 preserves the format-1.0 checks introduced in 0.1.0:

- required sections and basic types;
- supported autonomy, evidence type, and evidence status values;
- unique model, contribution, and evidence identifiers;
- valid model and evidence references;
- HTTP(S) URL and Git commit evidence formats;
- safe repository-relative paths with optional existence checks;
- selected high-confidence secret signatures;
- deterministic rendering without generated timestamps.

It deliberately does **not** claim to prove authorship, model identity, model execution, code quality, or legal compliance. Those limits must remain visible.

## Release-quality evidence

Flagship CI runs Ubuntu, Windows, and macOS across CPython 3.11, 3.12, and 3.13. Each job uses the exact pinned build toolchain, builds wheel plus source distribution, installs/tests the wheel, validates the repository manifest, proves deterministic Markdown rendering, executes the real CLI 0/1/2 counter-proof, smokes `aim --version` outside checkout, and tests the complete source distribution.

Every candidate bundle includes `SHA256SUMS.txt`, CycloneDX 1.6 `ai-assistance-manifest.cdx.json`, and `RELEASE_EVIDENCE.json`. The receipt remains `PREPARED` and records `signed=false`, `attested=false`, `tagged=false`, `published=false`, and `released=false`.

After the 9-job matrix, a guarded owner/same-repository job signs the canonical Ubuntu/Python 3.11 wheel using GitHub/Sigstore SLSA provenance and independently runs `gh attestation verify` constrained by repository, signer workflow, source ref, source digest, and GitHub-hosted runner policy. The attestation receipt records `publication_authorized=false`.

Signed provenance is evidence, not release authority. Publication requires a separate reviewed change plus post-publication read-back verification.

## CI integration

```yaml
- name: Validate AI assistance declaration
  run: |
    python -m pip install .
    aim validate AI_ASSISTANCE.json --check-files --root .
    aim render AI_ASSISTANCE.json --output /tmp/AI_ASSISTANCE.md --check-files --root .
    diff -u AI_ASSISTANCE.md /tmp/AI_ASSISTANCE.md
```

The repository uses this gate on itself in addition to release-quality checks.

## Design principles

- **Human authority stays explicit.** A model cannot silently become the final decision-maker.
- **Evidence is typed and status-aware.** Unknown or blocked work is not painted green.
- **The source is diffable.** Canonical JSON and deterministic Markdown keep review useful.
- **Validation is local-first.** The CLI does not make network requests.
- **Public means public-safe.** Secret signatures and unsafe paths fail validation.
- **Extensions are namespaced.** Experimental top-level data must start with `x-`.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests scripts
python scripts/check_release_policy.py
python scripts/verify_counterproof.py
python -m pip wheel . --no-deps -w dist
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [MIGRATION-0.2.md](MIGRATION-0.2.md), and [docs/RELEASE.md](docs/RELEASE.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
