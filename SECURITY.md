# Security policy

## Supported versions

Security fixes are provided for the latest tagged minor release.

## Scanner boundary

Repo Doctor is a read-only static auditor, not a sandbox or malware scanner. Do not use it to make untrusted repositories safe to execute. The tool never runs repository code, imports inspected modules, evaluates configuration expressions, or sends source to a network service.

Controls include:

- descriptor-relative `openat` confinement where supported and a portable root/component/opened-file identity backend elsewhere, with unconditional symlink, junction, and reparse-point skipping;
- deterministic exclusions and file, content, timeout, error, finding, baseline, report, and journal bounds;
- duplicate-key and unknown-field rejection for configuration, baselines, and consumed reports;
- credential redaction and control-character neutralization at finding construction and final JSON/human-output boundaries, including plugins, journals, and SBOM components;
- explicit trusted plugin registration with finding-contract validation;
- expiring, reasoned, exact-fingerprint suppressions that cannot change audit state;
- HTML escaping and bounded remediation locations;
- atomic report writes;
- process-locked, size-fenced, append-only hash-chained and typed-idempotent audit events;
- output/journal alias rejection and strict final-newline validation before journal replay or append;
- no runtime dependencies.

Reports, baselines, plans, SBOMs, and journals can reveal filenames and security findings. Store and share them according to the repository's sensitivity. Pattern matches can be false positives or miss encoded, split, encrypted, or unfamiliar credential formats.

Rule plugins are trusted application code. Do not load a plugin supplied by the repository under audit. The built-in CLI intentionally has no dynamic plugin discovery.

## Reporting a vulnerability

Use GitHub's private security advisory interface for this repository. Provide the affected version, a minimal synthetic repository, impact, and proposed mitigation. Never submit live credentials, proprietary source, or personal data.
