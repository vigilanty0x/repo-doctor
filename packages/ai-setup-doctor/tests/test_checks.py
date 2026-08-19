from __future__ import annotations

import subprocess
import unittest

from ai_setup_doctor.api import diagnose
from ai_setup_doctor.checks import (
    DEFAULT_TOOL_SPECS, CircuitBreaker, Doctor, ExecutionResult, ToolSpec,
)
from ai_setup_doctor.models import ContractError, EvidenceClass, ToolStatus

from helpers import FakeExecutor


class ToolSpecTests(unittest.TestCase):
    def test_default_inventory_has_required_tools(self) -> None:
        names = {spec.name for spec in DEFAULT_TOOL_SPECS}
        self.assertTrue({"Git", "Docker", "Python", "Node.js", "Ollama"}.issubset(names))
        self.assertTrue(any("CLI" in name for name in names))

    def test_path_command_rejected(self) -> None:
        with self.assertRaises(ContractError):
            ToolSpec("Bad", "/tmp/bad")

    def test_timeout_too_small_rejected(self) -> None:
        with self.assertRaises(ContractError):
            ToolSpec("Bad", "bad", timeout_seconds=0)

    def test_timeout_too_large_rejected(self) -> None:
        with self.assertRaises(ContractError):
            ToolSpec("Bad", "bad", timeout_seconds=31)

    def test_too_many_args_rejected(self) -> None:
        with self.assertRaises(ContractError):
            ToolSpec("Bad", "bad", tuple(str(i) for i in range(16)))


class DoctorTests(unittest.TestCase):
    spec = ToolSpec("Synthetic", "synthetic", ("--version",), 0.5)

    def doctor(self, executor: FakeExecutor, found: bool = True, breaker: CircuitBreaker | None = None) -> Doctor:
        finder = (lambda command: "/synthetic/bin/tool") if found else (lambda command: None)
        return Doctor(finder=finder, executor=executor, circuit_breaker=breaker)

    def test_missing_is_direct_proof_without_execution(self) -> None:
        executor = FakeExecutor(ExecutionResult(0, "unused"))
        result = self.doctor(executor, found=False).check(self.spec)
        self.assertEqual((result.status, result.evidence_class), (ToolStatus.MISSING, EvidenceClass.PROOF))
        self.assertEqual(executor.calls, [])

    def test_success_with_output_is_proof(self) -> None:
        result = self.doctor(FakeExecutor(ExecutionResult(0, "tool 1.2\n"))).check(self.spec)
        self.assertEqual(result.status, ToolStatus.INSTALLED)
        self.assertEqual(result.evidence_class, EvidenceClass.PROOF)
        self.assertEqual(result.version, "tool 1.2")

    def test_success_without_output_is_inference(self) -> None:
        result = self.doctor(FakeExecutor(ExecutionResult(0))).check(self.spec)
        self.assertEqual(result.status, ToolStatus.INSTALLED)
        self.assertEqual(result.evidence_class, EvidenceClass.INFERENCE)

    def test_stderr_can_carry_version(self) -> None:
        result = self.doctor(FakeExecutor(ExecutionResult(0, stderr="tool 2.0"))).check(self.spec)
        self.assertEqual(result.version, "tool 2.0")

    def test_output_is_bounded(self) -> None:
        result = self.doctor(FakeExecutor(ExecutionResult(0, "x" * 1000))).check(self.spec)
        self.assertEqual(len(result.version or ""), 512)

    def test_nonzero_is_error_not_success(self) -> None:
        result = self.doctor(FakeExecutor(ExecutionResult(7, stderr="failed"))).check(self.spec)
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertEqual(result.error_code, "nonzero_exit")
        self.assertEqual(result.exit_code, 7)

    def test_timeout_is_blockage_not_success(self) -> None:
        result = self.doctor(FakeExecutor("timeout")).check(self.spec)
        self.assertEqual(result.status, ToolStatus.BLOCKED)
        self.assertEqual(result.evidence_class, EvidenceClass.BLOCKAGE)
        self.assertEqual(result.error_code, "timeout")

    def test_permission_is_blockage(self) -> None:
        result = self.doctor(FakeExecutor(PermissionError("no"))).check(self.spec)
        self.assertEqual((result.status, result.error_code), (ToolStatus.BLOCKED, "permission_denied"))

    def test_oserror_is_visible_error(self) -> None:
        result = self.doctor(FakeExecutor(OSError("broken"))).check(self.spec)
        self.assertEqual((result.status, result.error_code), (ToolStatus.ERROR, "execution_error"))

    def test_executor_receives_exact_argv_and_timeout(self) -> None:
        executor = FakeExecutor(ExecutionResult(0, "ok"))
        self.doctor(executor).check(self.spec)
        self.assertEqual(executor.calls, [("/synthetic/bin/tool", ("--version",), 0.5)])

    def test_diagnose_rejects_empty_inventory(self) -> None:
        with self.assertRaises(ContractError):
            self.doctor(FakeExecutor(ExecutionResult(0))).diagnose([])

    def test_api_supports_injection(self) -> None:
        report = diagnose(
            [self.spec], finder=lambda command: "/synthetic/bin/tool",
            executor=FakeExecutor(ExecutionResult(0, "synthetic 1")),
        )
        self.assertEqual(report.summary["installed"], 1)


class CircuitBreakerTests(unittest.TestCase):
    def test_opens_at_threshold(self) -> None:
        now = [10.0]
        breaker = CircuitBreaker(2, 5, clock=lambda: now[0])
        self.assertTrue(breaker.allow("tool"))
        breaker.failure("tool")
        self.assertTrue(breaker.allow("tool"))
        breaker.failure("tool")
        self.assertFalse(breaker.allow("tool"))

    def test_half_open_after_cooldown(self) -> None:
        now = [10.0]
        breaker = CircuitBreaker(1, 5, clock=lambda: now[0])
        breaker.failure("tool")
        now[0] = 15.0
        self.assertTrue(breaker.allow("tool"))

    def test_success_resets_failures(self) -> None:
        breaker = CircuitBreaker(2, 5)
        breaker.failure("tool")
        breaker.success("tool")
        breaker.failure("tool")
        self.assertTrue(breaker.allow("tool"))

    def test_state_is_per_tool(self) -> None:
        breaker = CircuitBreaker(1, 5)
        breaker.failure("one")
        self.assertFalse(breaker.allow("one"))
        self.assertTrue(breaker.allow("two"))

    def test_doctor_skips_executor_when_open(self) -> None:
        breaker = CircuitBreaker(1, 5)
        breaker.failure("synthetic")
        executor = FakeExecutor(ExecutionResult(0, "would succeed"))
        result = Doctor(
            finder=lambda command: "/synthetic/bin/tool", executor=executor, circuit_breaker=breaker
        ).check(ToolSpec("Synthetic", "synthetic"))
        self.assertEqual((result.status, result.error_code), (ToolStatus.BLOCKED, "circuit_open"))
        self.assertEqual(executor.calls, [])

    def test_invalid_threshold_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CircuitBreaker(0)


if __name__ == "__main__":
    unittest.main()

