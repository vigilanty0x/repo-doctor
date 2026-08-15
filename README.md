# Migration Verifier

## Purpose

Transactional SQLite migration ordering, digest, execution, and rollback proof. The package is standard-library-only and designed for deterministic local use with synthetic or caller-controlled JSON.

## Non-goals

It does not apply migrations to a real database, establish who published a digest, or support SQLite statements with external side effects.

## Install

Requires Python 3.11 or newer.

```bash
python -m pip install .
```

## CLI and API

Pass a JSON object by path or standard input. Success is emitted as machine-readable JSON; validation failures return exit status 2 without a traceback.

```bash
migration-verifier examples/basic.json
python -m migration_verifier.cli examples/basic.json
```

The public API is `migration_verifier.core.run(data)`. Lower-level functions remain available for focused library use; inspect their signatures for supported keyword options.

## Example

The example validates one synthetic CREATE TABLE migration against a separately supplied digest.

```bash
migration-verifier examples/basic.json
```

All example content is synthetic and safe to publish.

## Security and trust model

Conservative statement checks and a SQLite authorizer block attachment, detachment, vacuum output, transaction control, pragmas, and extension loading. Supported statements execute inside one wrapper transaction and are rolled back.

The caller remains responsible for authenticating inputs and enforcing returned decisions at the real I/O or authorization boundary. Invalid and inconclusive inputs fail visibly rather than producing a healthy or verified claim.

## Limitations

A migration is only labeled verified when every digest matches an independently supplied trusted_digests map. Self-supplied matching digests produce self_consistent, not verified.

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

