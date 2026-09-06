# State Machine Visualizer

## Purpose

Validate a reachable finite state machine and render Mermaid `stateDiagram-v2` text.

## Non-goals

The package does not execute state transitions, render images, or accept Mermaid syntax as input.

## Install

Requires Python 3.11 or newer: `python -m pip install .`

## API

`evaluate(record)` accepts `name`, unique `states`, `initial`, and two-item `transitions`. Mermaid nodes use opaque `state_N` identifiers; labels are quoted separately.

## CLI

Run `state-machine-visualizer examples/valid.json` to print a receipt containing Mermaid text.

## Example

The synthetic example models queued, running, and done states.

## Security

Labels reject controls and newlines, are length-bounded, and never become Mermaid identifiers. Transitions must be unique and reference declared reachable states.

## Limits

At most 200 states, 1,000 transitions, 200 characters per label, and 64 KiB aggregate input.

## Tests

Run `python -m unittest discover -s tests -v` and `python scripts/check.py`; regressions cover newline/control injection and quote escaping.

## AI assistance

See `AI_ASSISTANCE.md`; validate generated diagrams before publishing.

## License

Apache-2.0; see `LICENSE`.
