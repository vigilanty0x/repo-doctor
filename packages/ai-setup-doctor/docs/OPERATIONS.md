# Operations

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Command or probe completed without blocked/error diagnostics |
| 2 | Diagnostic evidence includes a blocked or error result |
| 3 | Probe failed |
| 4 | Input or evidence contract failed |
| 5 | Local I/O failed |

## Probes

- `liveness` proves that the CLI process can construct its response.
- `readiness` proves that the bounded diagnostic contract initializes.
- `functional` runs a successful synthetic control and a timeout counter-example, asserts the timeout remains non-success, and checks deterministic replay identity.

Use `verify --journal` before consuming journal evidence. A corrupt or truncated journal is a blocking condition, not partial success. Reports are written through a same-directory temporary file, fsynced, and atomically replaced.

