# Failure Postmortem Kit

## Purpose

Generate deterministic, evidence-oriented Markdown postmortems with accountable follow-up actions.

## Non-goals

It does not investigate incidents, establish causality, assign blame, notify owners, or track action completion.

## Install

Requires Python 3.11 or newer.

```console
python -m pip install .
```

## CLI and API

Run the built-in positive and negative control:

```console
postmortem-kit probe
```

Process JSON from a file:

```console
postmortem-kit build --input examples/basic.json
```

The public Python seam is `failure_postmortem_kit.build`:

```python
from failure_postmortem_kit import build
```

Functions return structured JSON-compatible results and reject malformed input without raising validation exceptions.

## Example

A runnable input is provided at `examples/basic.json`. CLI output is deterministic and includes either a SHA-256 evidence field or an explicit validation failure.

## Security and trust model

Incident text, evidence, causes, and action fields are treated as untrusted and escaped for Markdown/HTML contexts. Exact schemas and non-empty evidence fail closed. The tool performs no network calls.

## Limitations

Lists are capped at 100 entries, strings and total output are bounded, and interpolated newlines and controls are rejected.

## Tests

Run the same local gates used by CI:

```console
python -m unittest discover -s tests -v
python scripts/check.py
python -m build --no-isolation
postmortem-kit probe
postmortem-kit build --input examples/basic.json
```

CI tests Python 3.11 and 3.12, installs the project and rebuilt wheel, imports the installed package, and exercises both the probe and example.

## AI disclosure

AI assistance supported defensive implementation, adversarial test design, and documentation. See [AI_ASSISTANCE.md](AI_ASSISTANCE.md) for scope and review expectations.

## License

Apache-2.0. See [LICENSE](LICENSE).

