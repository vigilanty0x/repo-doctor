# Repo Dependency Graph

## Purpose

Validate bounded declared repository dependencies and produce deterministic cycle, topology, DOT, and SHA-256 evidence.

## Non-goals

It does not scan repositories, resolve package manifests, access registries, or verify external dependency claims.

## Install

Requires Python 3.11 or newer.

```console
python -m pip install .
```

## CLI and API

Run the built-in positive and negative control:

```console
repo-deps probe
```

Process JSON from a file:

```console
repo-deps graph --input examples/basic.json
```

The public Python seam is `repo_dependency_graph.graph`:

```python
from repo_dependency_graph import graph
```

Functions return structured JSON-compatible results and reject malformed input without raising validation exceptions.

## Example

A runnable input is provided at `examples/basic.json`. CLI output is deterministic and includes either a SHA-256 evidence field or an explicit validation failure.

## Security and trust model

Repository nodes and edges are caller declarations. Names and edges must be unique, unknown dependencies fail closed, and output explicitly marks external verification as false. The tool performs no network calls.

## Limitations

At most 500 repositories and 5,000 edges are processed; topology is returned only for acyclic input.

## Tests

Run the same local gates used by CI:

```console
python -m unittest discover -s tests -v
python scripts/check.py
python -m build --no-isolation
repo-deps probe
repo-deps graph --input examples/basic.json
```

CI tests Python 3.11 and 3.12, installs the project and rebuilt wheel, imports the installed package, and exercises both the probe and example.

## AI disclosure

AI assistance supported defensive implementation, adversarial test design, and documentation. See [AI_ASSISTANCE.md](AI_ASSISTANCE.md) for scope and review expectations.

## License

Apache-2.0. See [LICENSE](LICENSE).

