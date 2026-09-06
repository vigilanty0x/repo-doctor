# Migration vers AI Assistance Manifest 0.2.0

AI Assistance Manifest 0.2.0 durcit le packaging, la CI et les preuves de release sans changer le format de manifeste JSON 1.0.

## Compatibilité

- Produit/distribution : `ai-assistance-manifest`.
- Namespace Python : `ai_assistance_manifest`.
- CLI : `aim`.
- Format de manifeste : toujours version 1.0.
- Les commandes `init`, `validate`, `render` et `schema` conservent leur contrat.
- Codes de sortie `validate` : `0` valide, `1` diagnostics de validation, `2` entrée illisible/invalide.

## Release gates

Le candidat 0.2 est `PREPARED`, pas publié. Avant toute publication : CI Ubuntu/Windows/macOS sur Python 3.11-3.13, wheel+sdist installables, tests complets, rendu Markdown déterministe, contre-preuves exit 1/2, smoke CLI hors checkout, sdist auto-auditable, SHA-256, CycloneDX 1.6, provenance GitHub/Sigstore vérifiée, compatibilité consommateurs, décision explicite de publication et vérification post-publication.

`release-policy.v1.json` garde `publish_enabled=false`.

## Rollback

Rollback vers 0.1.0. Le format JSON reste 1.0 et aucune base de données, aucun secret ni état distant n'est migré ; les manifestes 1.0 restent utilisables avec 0.1.0 sous réserve des validations déjà définies par cette version.

## Consolidation

`ai-project-provenance-badge` reste consolidé sous `packages/`. Cette migration ne l'archive ni ne le supprime. Toute décision d'archive exige inventaire consommateurs, compatibilité/redirect, rollback et approbation humaine explicite.
