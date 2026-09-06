# Contributing

Contributions are welcome when they keep the format small, reviewable, deterministic, and honest about uncertainty.

## Workflow

1. Open an issue for format changes or new normative fields.
2. Create a focused branch and keep unrelated changes out of the diff.
3. Add or update tests before changing validation behavior.
4. Update `SPEC.md`, the bundled JSON Schema, the template, and examples together.
5. Regenerate `AI_ASSISTANCE.md` from `AI_ASSISTANCE.json`.
6. Run the local verification commands.

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
PYTHONPATH=src python -m ai_assistance_manifest validate AI_ASSISTANCE.json --check-files --root .
PYTHONPATH=src python -m ai_assistance_manifest render AI_ASSISTANCE.json --output /tmp/AI_ASSISTANCE.md --check-files --root .
diff -u AI_ASSISTANCE.md /tmp/AI_ASSISTANCE.md
```

## Compatibility

Stable diagnostic codes and version 1.0 field meanings are public interfaces. Changes that break them require an explicit versioning decision and migration notes.

## AI-assisted contributions

AI assistance is welcome. Declare material assistance in `AI_ASSISTANCE.json` or in the pull-request description. A human contributor must understand the change, review the diff, and retain responsibility for submission.

Never submit secrets, private prompts, private repository context, personal data, or generated content that you do not have the right to license.

