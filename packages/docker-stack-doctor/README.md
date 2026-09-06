# Docker Stack Doctor

Verify Compose service health and exact stack evidence.

## Quick start

```bash
python -m pip install -e .
docker-stack-doctor record.json
```

The CLI emits deterministic fail-closed JSON plus a SHA-256 evidence identifier. Required fields: `stack`, `service_count`, `healthy_count`. Rule: every declared service must be healthy.

## Verify

```bash
python -m unittest discover -s tests -v
python scripts/check.py
```

Apache-2.0. Python 3.11+. Zero runtime dependencies.

