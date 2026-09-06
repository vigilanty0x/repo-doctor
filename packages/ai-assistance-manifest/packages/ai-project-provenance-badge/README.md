# AI Project Provenance Badge

## Purpose

Render a Markdown badge that documents a bounded AI-assistance declaration and structured artifact, test, and review digests.

## Non-goals

The package does not fetch evidence, validate signatures, authenticate issuers, or turn self-assertions into verified provenance.

## Install

Requires Python 3.11 or newer: `python -m pip install .`

## API

`evaluate(record)` requires project metadata, positive test count, safe HTTPS evidence URL, and exact structured `evidence` fields. Output is `documented-self-declaration` with `verified: false`.

## CLI

Run `ai-project-provenance-badge examples/valid.json` to print the receipt and Markdown.

## Example

The example uses synthetic placeholder digests and a reserved invalid domain; it is documentation, not attestation.

## Security

URLs require HTTPS, a normalized nonempty host, no credentials, controls, whitespace, or Markdown-breaking delimiters. Digests are strict lowercase SHA-256 strings.

## Limits

Input is capped at 32 KiB and URLs at 2,048 characters. Independently verified attestations are outside this implementation.

## Tests

Run `python -m unittest discover -s tests -v` and `python scripts/check.py`.

## AI assistance

See `AI_ASSISTANCE.md`; provenance statements require evidence-owner review.

## License

Apache-2.0; see `LICENSE`.
