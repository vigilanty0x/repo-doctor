# AI Setup Doctor

AI Setup Doctor is a zero-runtime-dependency CLI and Python API that explains whether a local AI development workstation has the expected tools. It checks Git, Docker, Python, Node.js, Ollama, and common AI CLIs without invoking a shell, and it never turns a failed check into a success.

The output is a deterministic schema-1.0 document. Every result explicitly says whether it is a **proof**, an **inference**, or a **blockage**. Synthetic fixtures make demos and counter-proofs reproducible without an account, network call, model, daemon, or private environment.

## Quick start

```bash
python -m ai_setup_doctor inventory
python -m ai_setup_doctor diagnose
python -m ai_setup_doctor diagnose --fixture examples/fixture.json --output report.json --journal evidence.jsonl
python -m ai_setup_doctor verify report.json
python -m ai_setup_doctor probe functional
python -m ai_setup_doctor demo demo-output
```

`diagnose` exits with `0` when no check is blocked or erroneous, `2` when a blocked/error result is preserved, and `4` for invalid input. Missing optional tools remain truthful `missing` results and are not treated as execution errors.

## What is checked

| Tool | Executable | Default evidence command |
| --- | --- | --- |
| Git | `git` | `git --version` |
| Docker | `docker` | `docker --version` |
| Python | `python` | `python --version` |
| Node.js | `node` | `node --version` |
| Ollama | `ollama` | `ollama --version` |
| OpenAI Codex CLI | `codex` | `codex --version` |
| Claude Code CLI | `claude` | `claude --version` |
| Gemini CLI | `gemini` | `gemini --version` |

Checks have a 2-second default timeout and an upper contract bound of 30 seconds. A per-executable circuit breaker opens after repeated execution failures and reports a visible `blocked` result. It never silently retries or substitutes a guessed success.

## Python API

```python
from ai_setup_doctor import diagnose

report = diagnose()
print(report.report_id)
print(report.to_dict())
```

Custom checks use `ToolSpec`, whose executable name, arguments, timeout, and total inventory are bounded. For deterministic tests, pass a synthetic `finder` and `Executor`; see `examples/fixture.json` and `docs/ARCHITECTURE.md`.

## Evidence and replay

- `proof`: direct PATH absence, successful version command, or observed non-zero exit.
- `inference`: the executable responded with exit code zero but supplied no version text.
- `blockage`: timeout, permission denial, start failure, or an open circuit prevented a complete check.
- `report_id`: SHA-256 of canonical diagnostics and summary, excluding clocks and host metadata.
- journal `event_id`: SHA-256 of event kind plus report ID. Re-appending the same report is a no-op.

The journal is newline-delimited JSON, append-only, locked during writes, flushed, and fsynced. A malformed, truncated, duplicated, or content-mismatched event blocks further appends.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/check.py
PYTHONPATH=src python -m ai_setup_doctor probe functional
PIP_NO_INDEX=1 python -m pip wheel . --no-deps --no-build-isolation
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the documents in `docs/`.

## License

Apache License 2.0. See [LICENSE](LICENSE).

