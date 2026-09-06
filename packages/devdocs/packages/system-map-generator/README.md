# System Map Generator

## Purpose

Validate bounded declared nodes and edges and produce deterministic Mermaid topology with SHA-256 evidence.

## Non-goals

It does not discover systems, query infrastructure, verify reachability, or establish runtime dependencies.

## Install

Requires Python 3.11 or newer.

```console
python -m pip install .
```

## CLI and API

Run the built-in positive and negative control:

```console
system-map probe
```

Process JSON from a file:

```console
system-map generate --input examples/basic.json
```

The public Python seam is `system_map_generator.generate`:

```python
from system_map_generator import generate
```

Functions return structured JSON-compatible results and reject malformed input without raising validation exceptions.

## Example

A runnable input is provided at `examples/basic.json`. CLI output is deterministic and includes either a SHA-256 evidence field or an explicit validation failure.

## Security and trust model

Node identifiers and labels are untrusted. Output uses opaque Mermaid node IDs and escaped, bounded labels; dangling and duplicate edges fail closed. The tool performs no network calls.

## Limitations

Maps are capped at 200 nodes and 1,000 directed edges and describe declared input only.

## Tests

Run the same local gates used by CI:

```console
python -m unittest discover -s tests -v
python scripts/check.py
python -m build --no-isolation
system-map probe
system-map generate --input examples/basic.json
```

CI tests Python 3.11 and 3.12, installs the project and rebuilt wheel, imports the installed package, and exercises both the probe and example.

## AI disclosure

AI assistance supported defensive implementation, adversarial test design, and documentation. See [AI_ASSISTANCE.md](AI_ASSISTANCE.md) for scope and review expectations.

## License

Apache-2.0. See [LICENSE](LICENSE).
