# Backup Verifier

## Purpose

Compare bounded expected and observed backup metadata for missing, unexpected, size, and SHA-256 mismatches.

## Non-goals

It does not read backup bytes, prove recoverability, authenticate storage, or perform restoration.

## Install

Requires Python 3.11 or newer.

```console
python -m pip install .
```

## CLI and API

Run the built-in positive and negative control:

```console
backup-verifier probe
```

Process JSON from a file:

```console
backup-verifier verify --expected-manifest-trusted --input examples/basic.json
```

The public Python seam is `backup_verifier.verify`:

```python
from backup_verifier import verify
```

Functions return structured JSON-compatible results and reject malformed input without raising validation exceptions.

## Example

A runnable input is provided at `examples/basic.json`. CLI output is deterministic and includes either a SHA-256 evidence field or an explicit validation failure.

## Security and trust model

Verification is metadata-only. The expected manifest is untrusted by default; authenticity requires the caller to establish and explicitly declare that expected manifest as trusted outside the compared input. The tool performs no network calls.

## Limitations

Paths, file counts, per-file sizes, and aggregate declared sizes are bounded. Hashes must be exact lowercase SHA-256 strings.

## Tests

Run the same local gates used by CI:

```console
python -m unittest discover -s tests -v
python scripts/check.py
python -m build --no-isolation
backup-verifier probe
backup-verifier verify --expected-manifest-trusted --input examples/basic.json
```

CI tests Python 3.11 and 3.12, installs the project and rebuilt wheel, imports the installed package, and exercises both the probe and example.

## AI disclosure

AI assistance supported defensive implementation, adversarial test design, and documentation. See [AI_ASSISTANCE.md](AI_ASSISTANCE.md) for scope and review expectations.

## License

Apache-2.0. See [LICENSE](LICENSE).

