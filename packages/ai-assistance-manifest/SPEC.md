# AI Assistance Manifest Specification 1.0

Status: initial public specification for version `0.1.0` of the reference CLI.

## 1. Purpose

An AI Assistance Manifest is a self-reported, reviewable declaration of human and AI participation in a software project. It records responsibility and evidence without claiming that a declaration alone proves authorship, model execution, security, quality, or legal compliance.

The canonical filename is `AI_ASSISTANCE.json`. UTF-8 JSON is normative. Duplicate object keys are invalid. A manifest larger than 1 MiB is rejected by the reference CLI.

## 2. Required sections

| Field | Meaning |
|---|---|
| `schema_version` | Exact format version. Version 1 requires `"1.0"`. |
| `project` | Project identity and at least one accountable owner. |
| `assistance` | Plain-language summary, autonomy level, and human review contract. |
| `models` | Systems used, identified by stable manifest-local IDs. |
| `contributions` | Separate human and AI contribution records. |
| `evidence` | Typed claims with explicit truth status and locations. |
| `limitations` | At least one material limitation of the declaration. |

Optional sections are `$schema`, `decisions`, and `incidents`. Experimental top-level extensions must use an `x-` prefix. Other unknown top-level fields are invalid.

The bundled JSON Schema is an ecosystem aid. The reference CLI additionally enforces cross-reference, safe-path, duplicate-key, file-existence, and secret-hygiene rules that JSON Schema alone does not express.

## 3. Autonomy

`assistance.autonomy` is one of:

- `assistive`: a human directly leads the work and uses AI for bounded assistance;
- `collaborative`: human and AI contributions are interleaved, with declared human review;
- `agentic`: an AI system executes multi-step work with bounded authority and human governance.

The value describes the declared workflow, not the capability or intelligence of a model.

## 4. Evidence

Every evidence item has a unique `id`, a `type`, a `status`, a `location`, and a description.

Types:

- `file`, `test`, or `report`: a safe repository-relative path;
- `commit`: a 7-64 digit hexadecimal Git object identifier;
- `url`: an HTTP(S) URL.

Statuses:

- `verified`: directly checked evidence supports the claim;
- `inferred`: evidence supports a conclusion that was not directly observed;
- `blocked`: a named dependency prevents verification or completion;
- `unknown`: the relevant fact has not been established.

The renderer preserves these statuses. It must not convert an uncertain state into success.

With `--check-files`, local evidence paths must exist below the selected repository root. Absolute paths, parent traversal, home-relative paths, and backslash-rooted paths are invalid even when file checks are disabled.

## 5. Cross-references

- Model IDs are unique.
- Evidence IDs are unique.
- AI contribution IDs are unique.
- Each `model_ref` resolves to a declared model.
- Each `evidence_refs` entry resolves to declared evidence.

## 6. Deterministic output

Given the same valid manifest, the renderer must produce byte-for-byte identical Markdown. It must not inject the current time, host, username, network state, or unordered runtime data. Arrays retain their declared order.

## 7. Security and privacy

The CLI operates locally and performs no network requests. It rejects several high-confidence secret patterns and unsafe file references. This is a guardrail, not a complete secret scanner. Maintainers remain responsible for reviewing the full diff and running dedicated secret-scanning tools before publication.

Do not include prompts, credentials, personal data, private repository details, customer information, proprietary topology, or private evidence in a public manifest.

## 8. Diagnostics and exit codes

Diagnostics use stable codes:

| Range | Meaning |
|---|---|
| `AAM001` | File or JSON loading failure |
| `AAM100-AAM106` | Required fields, types, and unknown fields |
| `AAM200-AAM208` | Version, enum, uniqueness, and reference errors |
| `AAM301-AAM304` | URL, commit, path, and file-existence errors |
| `AAM401` | Suspected secret |

Exit codes are `0` for success, `1` for validation findings, and `2` for usage or input errors.

## 9. Versioning

The schema uses a major/minor string. Additive, backward-compatible clarification may increment the minor version. Removing fields, changing required meaning, or changing accepted values requires a new major version. Implementations must fail closed on unsupported versions.

