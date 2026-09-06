# AI Assistance Manifest release contract

Candidate quality, signed provenance, publication, and post-publication verification are separate states.

- `PREPARED`: the exact source SHA passed tests/counter-proofs and produced installable wheel+sdist, checksums and SBOM.
- `ATTESTED`: the approved wheel has GitHub/Sigstore SLSA provenance that passed strict verification.
- `TAGGED`: an explicit tag was created after approval.
- `RELEASED`: immutable expected assets were published under that tag.
- `VERIFIED`: a separate read-back verified tag target, assets, checksums, provenance, installability and smoke behavior.
- `BLOCKED`: required evidence is missing or red.
- `ROLLED_BACK`: consumers returned to the documented 0.1.0 path while failed 0.2 evidence is preserved.

`release-policy.v1.json` deliberately sets `publish_enabled=false`; normal 0.2 CI can establish PREPARED and ATTESTED evidence only.

## Pre-publication evidence

The exact candidate must pass the complete 3 OS × 3 Python matrix, the full unit suite, deterministic render check, real `aim validate` positive/diagnostic/malformed counter-proofs, wheel and sdist installation checks, CLI smoke outside checkout, SHA-256 checksums, CycloneDX 1.6 SBOM, and strict GitHub/Sigstore provenance verification.

## Publication and rollback

Publication requires a separate reviewed change that enables one exact version/source SHA and defines immutable assets plus a read-only post-publication verifier. Rollback is 0.1.0; the JSON manifest schema remains 1.0 and no persistent runtime state is introduced.

## Archive gate

Portfolio consolidation is not archive authorization. Archival of the imported source project requires consumer inventory, compatibility/redirect evidence, rollback proof, and explicit human approval.
