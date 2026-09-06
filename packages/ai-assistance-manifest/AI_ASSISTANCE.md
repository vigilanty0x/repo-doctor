# AI Assistance Manifest

**Project:** ai-assistance-manifest
**Manifest version:** 1.0
**Project version:** 0.1.0
**Repository:** https://github.com/vigilanty0x/ai-assistance-manifest

An OpenAI coding assistant drafted the initial implementation from a human-selected public roadmap item. The repository owner authorized publication, set the public-only boundary, and retains final authority.

## Human oversight

- Autonomy level: `collaborative`
- Human review required: `yes`
- Final authority: vigilanty0x

### Owners

- vigilanty0x — Maintainer and final decision-maker

## Models and systems

| ID | Provider | Model | Roles |
|---|---|---|---|
| `openai-codex` | OpenAI | OpenAI Codex, GPT-5 family | Architecture, Implementation, Testing, Documentation |

## Human contributions

### vigilanty0x

**Roles:** Repository owner, Product owner, Final decision-maker

- Selected PUB-015 from the public roadmap
- Required complete separation from all private projects
- Authorized creation and publication of the standalone repository

## AI contributions

### `initial-build`

- Model reference: `openai-codex`
- Reviewed by: vigilanty0x
- Tasks: Translate the public project brief into a versioned format; Implement validation, rendering, and CLI behavior; Create tests and public documentation
- Artifacts: src/ai_assistance_manifest, tests, README.md, SPEC.md
- Evidence: unit-tests, ci-workflow, specification

## Evidence

| ID | Type | Status | Location | Description |
|---|---|---|---|---|
| `unit-tests` | test | `verified` | `tests` | Dependency-free unit and CLI test suite |
| `ci-workflow` | file | `verified` | `.github/workflows/ci.yml` | GitHub Actions validation on supported Python versions |
| `specification` | file | `verified` | `SPEC.md` | Version 1.0 format and behavior specification |

## Limitations

- The declaration is self-reported and cannot independently prove authorship or exact model execution.
- The secret scanner uses conservative signatures and cannot detect every credential format.
- The validator checks declarations and evidence references; it does not certify software quality or legal compliance.

## Decisions

- Use JSON as the canonical format so validation needs no YAML parser.
- Keep the runtime dependency-free on Python 3.11 and newer.
- Use stable diagnostic codes and deterministic Markdown output.

## Incidents and blocked states

- None declared.

---

This document is generated from `AI_ASSISTANCE.json`. Edit the manifest, not this file.
