# Security Policy

## Supported versions

Security fixes are applied to the latest released minor version.

## Reporting a vulnerability

Please use GitHub private vulnerability reporting for this repository. Do not open a public issue for an undisclosed vulnerability and do not include credentials, private manifests, personal data, or proprietary evidence in a report.

Include the affected version, a minimal synthetic reproduction, expected behavior, observed behavior, and impact. Reports are evaluated before any public disclosure timeline is proposed.

## Security model

The CLI parses local JSON and can optionally inspect whether declared relative paths exist. It does not execute manifest content, follow evidence links, invoke models, access Git history, or make network requests.

The built-in secret signatures are defense in depth. They do not replace a dedicated secret scanner or human review.

