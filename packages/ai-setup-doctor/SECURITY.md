# Security policy

## Supported versions

Security fixes are provided for the latest released minor version.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature for the repository. Do not open a public issue for a suspected vulnerability and do not include secrets or real workstation evidence in a report.

## Security properties

- Commands are argv arrays executed with `shell=False`.
- Executable checks use names resolved through `PATH`; fixture input cannot provide arbitrary executable paths.
- Timeouts, inventory size, arguments, fixture output, and serialized text are bounded.
- Execution errors remain `blocked` or `error` and cannot be represented as `installed`.
- Reports and journal events are content-addressed and validated before replay.
- The journal locks, appends, flushes, and fsyncs; corrupt or duplicate evidence fails closed.
- Demos and tests are synthetic and do not need credentials, accounts, daemons, or network access.

AI Setup Doctor reports local diagnostic evidence; it does not repair software, install packages, change configuration, or execute arbitrary commands from a report.

