# Port Conflict Doctor

Detect conflicting listeners with deterministic ownership evidence.

## Quick start

```bash
python -m pip install -e .
port-conflict-doctor record.json
```

The CLI emits deterministic fail-closed JSON plus a SHA-256 evidence identifier. Required fields: `port`, `owners`, `conflict`. Rule: a healthy port has at most one owner and no conflict.

## Verify

```bash
python -m unittest discover -s tests -v
python scripts/check.py
```

Apache-2.0. Python 3.11+. Zero runtime dependencies.

