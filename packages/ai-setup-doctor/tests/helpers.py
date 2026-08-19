from __future__ import annotations

import subprocess
from typing import Sequence

from ai_setup_doctor.checks import ExecutionResult
from ai_setup_doctor.models import EvidenceClass, ToolDiagnostic, ToolStatus


def diagnostic(name: str = "Git", status: ToolStatus = ToolStatus.INSTALLED) -> ToolDiagnostic:
    if status is ToolStatus.INSTALLED:
        return ToolDiagnostic(
            name, status, EvidenceClass.PROOF, "version command succeeded", (name.casefold(), "--version"),
            executable=f"/synthetic/bin/{name.casefold()}", version=f"{name} 1.0", exit_code=0,
        )
    if status is ToolStatus.MISSING:
        return ToolDiagnostic(
            name, status, EvidenceClass.PROOF, "not found", (name.casefold(), "--version"),
        )
    return ToolDiagnostic(
        name, status, EvidenceClass.BLOCKAGE, "check blocked", (name.casefold(), "--version"),
        executable=f"/synthetic/bin/{name.casefold()}", error_code="timeout",
    )


class FakeExecutor:
    def __init__(self, action: object) -> None:
        self.action = action
        self.calls: list[tuple[str, tuple[str, ...], float]] = []

    def run(self, executable: str, args: Sequence[str], timeout_seconds: float) -> ExecutionResult:
        self.calls.append((executable, tuple(args), timeout_seconds))
        if isinstance(self.action, BaseException):
            raise self.action
        if self.action == "timeout":
            raise subprocess.TimeoutExpired([executable, *args], timeout_seconds)
        assert isinstance(self.action, ExecutionResult)
        return self.action

