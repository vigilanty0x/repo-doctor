# Event Log Explorer

## Purpose

Inspect bounded, contiguous event timelines and optionally validate a per-event SHA-256 chain against a separately supplied expected head.

## Non-goals

Contiguous sequence numbers or self-contained hashes do not prove append-only storage, origin, timestamp truth, or authenticity. This tool never labels them as such.

## Install

Requires Python 3.11 or newer: `python -m pip install .`

## API

`evaluate(record, expected_head_sha256=...)` requires `stream` and `events`. Without hash fields and the separate keyword argument, the result is explicitly `structural-only`. An expected head embedded in the event record is rejected; the keyword value must come from a separately trusted channel.

## CLI

Run `event-log-explorer examples/valid.json`; the example deliberately reports structural inspection only.

## Example

Events use contiguous integer `sequence`, bounded `type`, and optional object `payload`. A chained event adds `previous_sha256` and `event_sha256` to every event.

## Security

Unexpected event fields, partial chains, digest mismatches, oversized payloads, and non-JSON numeric values fail closed.

## Limits

At most 1,000 events, 8 KiB per payload, and 128 KiB aggregate input. The expected head is only as trustworthy as its external delivery path.

## Tests

Run `python -m unittest discover -s tests -v` and `python scripts/check.py`.

## AI assistance

See `AI_ASSISTANCE.md`; a human must assess provenance and storage controls.

## License

Apache-2.0; see `LICENSE`.
