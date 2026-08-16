# Config Drift Detector

Compare expected and actual configuration digests without secrets.

## Quick start

```bash
python -m pip install -e .
config-drift-detector record.json
```

The CLI emits deterministic fail-closed JSON plus a SHA-256 evidence identifier. Required fields: `component`, `expected_digest`, `actual_digest`. Rule: expected and actual digests must match.

## Verify

```bash
python -m unittest discover -s tests -v
python scripts/check.py
```

Apache-2.0. Python 3.11+. Zero runtime dependencies.

