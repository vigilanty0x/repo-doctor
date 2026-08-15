# Healthcheck Hub

Aggregate component healthchecks into fail-closed evidence.

## Quick start

```bash
python -m pip install -e .
healthcheck-hub record.json
```

The CLI emits deterministic fail-closed JSON plus a SHA-256 evidence identifier. Required fields: `service`, `check_count`, `healthy_count`. Rule: every registered check must be healthy.

## Verify

```bash
python -m unittest discover -s tests -v
python scripts/check.py
```

Apache-2.0. Python 3.11+. Zero runtime dependencies.

