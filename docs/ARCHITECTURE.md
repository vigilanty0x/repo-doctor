# Architecture

## Boundaries

`ToolSpec` is the only description of a command check. It accepts a bounded executable **name**, up to 15 bounded arguments, and a timeout between 0.01 and 30 seconds. `Doctor` resolves the name through an injected finder and calls an injected executor without a shell.

The production executor uses `subprocess.run`. The synthetic executor accepts a strict fixture schema and can return success, non-zero exit, timeout, permission denial, or start failure. Both reach the same diagnostic mapping.

## Data flow

1. Resolve executable name.
2. Refuse execution while its circuit is open.
3. Run one version command under a timeout.
4. Map the observed outcome to an explicit status and evidence class.
5. Sort diagnostics and create a canonical content hash.
6. Optionally atomically write a report and append an idempotent journal event.

No repair, install, login, daemon start, remote request, or arbitrary report command exists.

## Failure model

| Observation | Status | Evidence class |
| --- | --- | --- |
| Not on PATH | `missing` | `proof` |
| Exit 0 with version | `installed` | `proof` |
| Exit 0 without version | `installed` | `inference` |
| Non-zero exit | `error` | `proof` |
| Timeout or permission denial | `blocked` | `blockage` |
| Process start error | `error` | `blockage` |
| Open circuit | `blocked` | `blockage` |

Circuit state is deliberately process-local. It prevents repeated failing calls during one diagnostic service lifetime without inventing persistent host state.

