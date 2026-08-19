# Dependency Drift Reporter

## Purpose

Compare declared and installed dependency-version maps and return a deterministic structured drift report.

## Non-goals

The package does not inspect an environment, resolve versions, query registries, or decide whether drift is exploitable.

## Install

Requires Python 3.11 or newer: `python -m pip install .`

## API

`evaluate(record)` accepts nonempty `manifest` and `installed` maps. Drift produces `status: failed` while retaining every `{name, declared, installed}` difference in `drift_report`.

## CLI

Run `dependency-drift-reporter examples/valid.json`; exit status 2 indicates drift or invalid input.

## Example

The synthetic example contains matching Python and tool versions.

## Security

Names, versions, map size, aggregate size, and JSON numbers are bounded or validated. Malformed maps fail without fabricating a report.

## Limits

At most 2,000 entries per map and 64 KiB aggregate input. Version strings are compared exactly, not semantically.

## Tests

Run `python -m unittest discover -s tests -v` and `python scripts/check.py`.

## AI assistance

See `AI_ASSISTANCE.md`; dependency-risk decisions require maintainer review.

## License

Apache-2.0; see `LICENSE`.
