# Source oracle, never a runtime plugin

`dependency_drift_reporter_core.py` preserves the exact acquired core from
`vigilanty0x/dependency-drift-reporter`, commit
`5af035db71c6cbd0c3f168929714a6d49994526b`, path
`src/dependency_drift_reporter/core.py`, Git blob
`d35b3ec53becde100115177a0c580399a0f5e159`.

SHA-256: `7a0ead0beb9a0150e4352d41966847c52736e744d311ed1c1ee11ed678f1ff90`.

Source project author: vigilanty0x. License declared by its preserved README
and pyproject: Apache-2.0; the Apache-2.0 license text is retained at the root of
Repo Doctor. Acquired bytes are verified against the saved source record and
Git blob identity. Tests import this trusted, fixed local oracle only. No target
repository code is dynamically loaded by the product.

`env_example_guard_core.py` preserves the acquired `env-example-guard` core,
commit `4df3eb9ae1347c5f03618b78e2a5a33507750c75`, path
`src/env_example_guard/core.py`, SHA-256
`ae6effa36178ceeafbe622094a5b979d9d389e825f0c5be723c6ea6a25823ee2`.
It has the same declared Apache-2.0 license and author. Its real `check()`
function is used only in synthetic parity tests, never imported by the scanner.
