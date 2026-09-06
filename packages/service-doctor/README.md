# Service Doctor

Diagnose service health, latency, and exact evidence.

## Quick start

```bash
python -m pip install -e .
service-doctor record.json
```

The CLI emits deterministic JSON with a fail-closed status and a SHA-256 evidence identifier. Required fields: `service`, `status`, `latency_ms`. Rule: status must be healthy and latency bounded.

## Development

```bash
python -m unittest discover -s tests -v
python scripts/check.py
```

Apache-2.0 licensed. No runtime dependencies.

