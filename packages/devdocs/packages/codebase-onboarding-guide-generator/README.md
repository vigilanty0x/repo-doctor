# Codebase Onboarding Guide Generator

## Purpose

Render deterministic Markdown onboarding notes from bounded project, entrypoint, command, and test metadata.

## Non-goals

This package does not inspect a repository, execute commands, or prove that supplied paths and commands exist.

## Install

Requires Python 3.11 or newer: `python -m pip install .`

## API

`evaluate(record)` returns a JSON-compatible receipt. Required fields are `project`, `entrypoints`, `commands`, and `tests`.

## CLI

Run `codebase-onboarding-guide-generator examples/valid.json`. Exit status is 0 for `passed` and 2 otherwise; malformed JSON also produces structured failure JSON.

## Example

`examples/valid.json` is synthetic. Its Markdown output escapes ordinary Markdown and chooses safe backtick fences for command/test code spans.

## Security

Single-line text, list counts, item sizes, and aggregate input are bounded. Control characters are rejected. Treat supplied commands as display text, never as trusted shell input.

## Limits

At most 50 items per section, 500 characters per item, and 32 KiB per input record. Rendering does not validate repository semantics.

## Tests

Run `python -m unittest discover -s tests -v` and `python scripts/check.py`.

## AI assistance

See `AI_ASSISTANCE.md`. AI-assisted changes still require human review before release.

## License

Apache-2.0; see `LICENSE`.
