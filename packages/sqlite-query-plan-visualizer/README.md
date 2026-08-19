# SQLite Query Plan Visualizer

## Purpose

Generate a real `EXPLAIN QUERY PLAN` result for one query against a validated, isolated in-memory SQLite fixture.

## Non-goals

The package does not connect to caller databases, accept caller-authored DDL, execute application queries, or accept plan strings as evidence.

## Install

Requires Python 3.11 or newer: `python -m pip install .`

## API

`evaluate(record)` accepts `query`, structured `fixture`, and optional scalar `parameters`. Fixture tables, columns, types, rows, and indexes are constructed from allowlisted structures.

## CLI

Run `sqlite-query-plan-visualizer examples/valid.json` to print SQLite's plan rows.

## Example

The example creates an in-memory `items` table and index, then plans a parameterized select.

## Security

An SQLite authorizer permits only select/read/function planning operations and denies writes, DDL, attach, pragma, and dangerous file/extension functions. Multiple statements and `WITH DELETE` fail.

## Limits

The fixture is bounded to 25 tables, 50 indexes, 1,000 rows per table, a 10,000-character query, 100 parameters, and 128 KiB input.

## Tests

Run `python -m unittest discover -s tests -v` and `python scripts/check.py`.

## AI assistance

See `AI_ASSISTANCE.md`; production performance conclusions require real workload analysis.

## License

Apache-2.0; see `LICENSE`.
