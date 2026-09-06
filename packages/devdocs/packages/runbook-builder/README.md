# Runbook Builder

## Purpose

Create deterministic operational runbooks with mandatory ownership, trigger, steps, verification, and rollback guidance.

## Non-goals

It does not execute operational steps, validate commands, contact owners, or guarantee recovery.

## Install

Requires Python 3.11 or newer.

```console
python -m pip install .
```

## CLI and API

Run the built-in positive and negative control:

```console
runbook-builder probe
```

Process JSON from a file:

```console
runbook-builder build --input examples/basic.json
```

The public Python seam is `runbook_builder.build`:

```python
from runbook_builder import build
```

Functions return structured JSON-compatible results and reject malformed input without raising validation exceptions.

## Example

A runnable input is provided at `examples/basic.json`. CLI output is deterministic and includes either a SHA-256 evidence field or an explicit validation failure.

## Security and trust model

All text is bounded and escaped for Markdown/HTML contexts. Newlines and control characters in interpolated fields fail closed. The tool performs no network calls.

## Limitations

Each procedural list is capped at 100 non-empty strings and rendered output is capped at 100,000 characters.

## Tests

Run the same local gates used by CI:

```console
python -m unittest discover -s tests -v
python scripts/check.py
python -m build --no-isolation
runbook-builder probe
runbook-builder build --input examples/basic.json
```

CI tests Python 3.11 and 3.12, installs the project and rebuilt wheel, imports the installed package, and exercises both the probe and example.

## AI disclosure

AI assistance supported defensive implementation, adversarial test design, and documentation. See [AI_ASSISTANCE.md](AI_ASSISTANCE.md) for scope and review expectations.

## License

Apache-2.0. See [LICENSE](LICENSE).

