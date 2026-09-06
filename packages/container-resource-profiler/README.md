# Container Resource Profiler

## Purpose

Normalize bounded caller-supplied CPU, memory, transfer, and startup measurements into a deterministic profile.

## Non-goals

The package does not start or inspect containers, sample cgroups, or independently observe any metric.

## Install

Requires Python 3.11 or newer: `python -m pip install .`

## API

`evaluate(record)` validates `scenario`, `cpu_percent`, `memory_mb`, `io_mb`, `network_mb`, and `startup_ms`. Output says `supplied-measurements` and `observed_by_tool: false`.

## CLI

Run `container-resource-profiler examples/valid.json` to normalize the synthetic sample.

## Example

The example values are illustrative and are not observations made by this tool.

## Security

Booleans, NaN, infinities, negative values, unrealistic extremes, controls, oversized input, and malformed records fail closed.

## Limits

CPU is 0-100%; memory is positive up to 1 TiB; transfers are capped at one billion MiB; startup is positive up to one day.

## Tests

Run `python -m unittest discover -s tests -v` and `python scripts/check.py`.

## AI assistance

See `AI_ASSISTANCE.md`; measurement methodology requires human review.

## License

Apache-2.0; see `LICENSE`.
