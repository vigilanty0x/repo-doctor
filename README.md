# SQLite Health Doctor

Read-only SQLite integrity, foreign-key, table, and index diagnostics.

Public offline Python MVP using only the standard library. Inputs are bounded, failures remain visible, and all examples/tests use synthetic data.

## CLI

```bash
python -m sqlite_health_doctor.cli input.json
python -m unittest discover -s tests -v
python scripts/check.py
```

The public Python API is `sqlite_health_doctor.core.run(data)`. The CLI accepts the same JSON object from a path or standard input and emits machine-readable JSON.

Apache License 2.0.

