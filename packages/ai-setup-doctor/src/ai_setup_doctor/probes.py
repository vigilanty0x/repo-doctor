"""Operational probes, including a deterministic failure counter-proof."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .checks import Doctor, ToolSpec
from .fixtures import FixtureEnvironment
from .models import ToolStatus


@dataclass(frozen=True, slots=True)
class ProbeResult:
    mode: str
    healthy: bool
    checks: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "1.0", "mode": self.mode, "healthy": self.healthy, "checks": list(self.checks)}


def liveness_probe() -> ProbeResult:
    return ProbeResult("liveness", True, ({"name": "process", "passed": True},))


def readiness_probe() -> ProbeResult:
    try:
        ToolSpec("Synthetic", "synthetic", ("--version",), 0.1)
        passed = True
        detail = "diagnostic contract accepted bounded configuration"
    except Exception as exc:  # defensive: readiness must expose contract failure
        passed = False
        detail = f"contract initialization failed: {type(exc).__name__}"
    return ProbeResult("readiness", passed, ({"name": "contract", "passed": passed, "detail": detail},))


def functional_probe() -> ProbeResult:
    fixture = FixtureEnvironment.from_dict({
        "schema_version": "1.0",
        "tools": [
            {
                "name": "Control Tool", "command": "control-tool", "version_args": ["--version"],
                "timeout_seconds": 0.1, "present": True,
                "behavior": {"kind": "success", "stdout": "control 1.0"},
            },
            {
                "name": "Failure Counter-proof", "command": "failure-tool", "version_args": ["--version"],
                "timeout_seconds": 0.1, "present": True,
                "behavior": {"kind": "timeout"},
            },
        ],
    })
    report = Doctor(finder=fixture.finder, executor=fixture.executor).diagnose(fixture.specs)
    by_name = {item.tool: item for item in report.diagnostics}
    control = by_name["Control Tool"].status is ToolStatus.INSTALLED
    counter = by_name["Failure Counter-proof"].status is ToolStatus.BLOCKED
    failure_not_success = by_name["Failure Counter-proof"].status is not ToolStatus.INSTALLED
    checks = (
        {"name": "control_success", "passed": control},
        {"name": "timeout_detected", "passed": counter},
        {"name": "failure_not_transformed_to_success", "passed": failure_not_success},
        {"name": "report_replay_id", "passed": report.report_id == Doctor(
            finder=fixture.finder,
            executor=FixtureEnvironment.from_dict({
                "schema_version": "1.0",
                "tools": [
                    {
                        "name": "Control Tool", "command": "control-tool", "version_args": ["--version"],
                        "timeout_seconds": 0.1, "present": True,
                        "behavior": {"kind": "success", "stdout": "control 1.0"},
                    },
                    {
                        "name": "Failure Counter-proof", "command": "failure-tool", "version_args": ["--version"],
                        "timeout_seconds": 0.1, "present": True,
                        "behavior": {"kind": "timeout"},
                    },
                ],
            }).executor,
        ).diagnose(fixture.specs).report_id},
    )
    return ProbeResult("functional", all(item["passed"] for item in checks), checks)

