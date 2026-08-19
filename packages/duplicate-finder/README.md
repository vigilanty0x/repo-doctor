# Duplicate Finder

## Purpose

Canonical exact and normalized duplicate grouping for JSON records. The package is standard-library-only and designed for deterministic local use with synthetic or caller-controlled JSON.

## Non-goals

It does not perform fuzzy entity resolution, mutate records, or decide which duplicate should survive.

## Install

Requires Python 3.11 or newer.

```bash
python -m pip install .
```

## CLI and API

Pass a JSON object by path or standard input. Success is emitted as machine-readable JSON; validation failures return exit status 2 without a traceback.

```bash
duplicate-finder examples/basic.json
python -m duplicate_finder.cli examples/basic.json
```

The public API is `duplicate_finder.core.run(data)`. Lower-level functions remain available for focused library use; inspect their signatures for supported keyword options.

## Example

The example finds a whitespace/case-normalized duplicate pair.

```bash
duplicate-finder examples/basic.json
```

All example content is synthetic and safe to publish.

## Security and trust model

Records, fields, identifiers, JSON values, and aggregate bytes are validated. Requested fields must exist, and identifiers must be unique strings.

The caller remains responsible for authenticating inputs and enforcing returned decisions at the real I/O or authorization boundary. Invalid and inconclusive inputs fail visibly rather than producing a healthy or verified claim.

## Limitations

Normalization only trims, case-folds, and collapses whitespace; domain-specific normalization remains caller work.

## Tests

Run the full local contract:

```bash
python -m unittest discover -s tests -v
python scripts/check.py
python -m build --no-isolation
```

CI exercises Python 3.11 and 3.12, builds and installs the wheel, then runs tests, the public-boundary check, the module example, and the installed console command.

## AI assistance

AI-assisted contribution details and validation expectations are documented in [AI_ASSISTANCE.md](AI_ASSISTANCE.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).

