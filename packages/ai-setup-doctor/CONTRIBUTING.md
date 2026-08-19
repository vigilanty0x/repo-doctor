# Contributing

Thank you for improving AI Setup Doctor.

1. Keep runtime dependencies at zero unless a proposal demonstrates a material safety benefit.
2. Add tests at the public contract or execution boundary for every behavior change.
3. Preserve explicit failure states: an error, timeout, denial, or circuit-open result must never become success.
4. Use only synthetic fixtures in tests, examples, issues, and pull requests.
5. Run the unit suite, public-boundary check, functional probe, and offline wheel build before submitting a change.

Commits should be small and descriptive. Pull requests should explain the observable behavior, risks, verification commands, and compatibility impact. Do not include credentials, host inventories, account identifiers, real command output, or private infrastructure references.

