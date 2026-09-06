"""Bounded executable checks with timeouts and per-tool circuit breakers."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
import time
from typing import Callable, Iterable, Protocol, Sequence

from .models import ContractError, DiagnosticReport, EvidenceClass, ToolDiagnostic, ToolStatus


MAX_OUTPUT_CHARS = 512
MAX_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    command: str
    version_args: tuple[str, ...] = ("--version",)
    timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not self.name or len(self.name) > 64:
            raise ContractError("tool spec name must contain 1 to 64 characters")
        if not self.command or len(self.command) > 256 or "/" in self.command or "\\" in self.command:
            raise ContractError("tool command must be a bounded executable name, not a path")
        if not 0.01 <= self.timeout_seconds <= MAX_TIMEOUT_SECONDS:
            raise ContractError(f"timeout_seconds must be between 0.01 and {MAX_TIMEOUT_SECONDS}")
        if len(self.version_args) > 15 or any(not arg or len(arg) > 256 for arg in self.version_args):
            raise ContractError("version_args are invalid")


DEFAULT_TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec("Git", "git"),
    ToolSpec("Docker", "docker"),
    ToolSpec("Python", "python", ("--version",)),
    ToolSpec("Node.js", "node"),
    ToolSpec("Ollama", "ollama"),
    ToolSpec("OpenAI Codex CLI", "codex"),
    ToolSpec("Claude Code CLI", "claude"),
    ToolSpec("Gemini CLI", "gemini"),
)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


class Executor(Protocol):
    def run(self, executable: str, args: Sequence[str], timeout_seconds: float) -> ExecutionResult: ...


class SubprocessExecutor:
    """Executes one argv array without a shell."""

    def run(self, executable: str, args: Sequence[str], timeout_seconds: float) -> ExecutionResult:
        completed = subprocess.run(
            [executable, *args],
            capture_output=True,
            check=False,
            shell=False,
            text=True,
            timeout=timeout_seconds,
        )
        return ExecutionResult(completed.returncode, completed.stdout, completed.stderr)


@dataclass(slots=True)
class _CircuitState:
    failures: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 2,
        cooldown_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 1 <= failure_threshold <= 10:
            raise ValueError("failure_threshold must be between 1 and 10")
        if not 0.01 <= cooldown_seconds <= 3600:
            raise ValueError("cooldown_seconds must be between 0.01 and 3600")
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._states: dict[str, _CircuitState] = {}

    def allow(self, key: str) -> bool:
        state = self._states.setdefault(key, _CircuitState())
        if state.opened_at is None:
            return True
        if self._clock() - state.opened_at >= self.cooldown_seconds:
            state.failures = 0
            state.opened_at = None
            return True
        return False

    def success(self, key: str) -> None:
        self._states[key] = _CircuitState()

    def failure(self, key: str) -> None:
        state = self._states.setdefault(key, _CircuitState())
        state.failures += 1
        if state.failures >= self.failure_threshold:
            state.opened_at = self._clock()


def _excerpt(stdout: str, stderr: str) -> str:
    combined = stdout.strip() or stderr.strip()
    return " ".join(combined.replace("\r", "\n").splitlines())[:MAX_OUTPUT_CHARS]


class Doctor:
    def __init__(
        self,
        *,
        finder: Callable[[str], str | None] = shutil.which,
        executor: Executor | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.finder = finder
        self.executor = executor or SubprocessExecutor()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    def check(self, spec: ToolSpec) -> ToolDiagnostic:
        command = (spec.command, *spec.version_args)
        executable = self.finder(spec.command)
        if executable is None:
            return ToolDiagnostic(
                spec.name, ToolStatus.MISSING, EvidenceClass.PROOF,
                f"{spec.command!r} was not found on PATH.", command,
            )
        if not self.circuit_breaker.allow(spec.command):
            return ToolDiagnostic(
                spec.name, ToolStatus.BLOCKED, EvidenceClass.BLOCKAGE,
                "The check was skipped because the circuit breaker is open after repeated failures.",
                command, executable=executable, error_code="circuit_open",
            )
        try:
            result = self.executor.run(executable, spec.version_args, spec.timeout_seconds)
        except subprocess.TimeoutExpired:
            self.circuit_breaker.failure(spec.command)
            return ToolDiagnostic(
                spec.name, ToolStatus.BLOCKED, EvidenceClass.BLOCKAGE,
                f"The version check exceeded the {spec.timeout_seconds:g}s timeout.",
                command, executable=executable, error_code="timeout",
            )
        except PermissionError:
            self.circuit_breaker.failure(spec.command)
            return ToolDiagnostic(
                spec.name, ToolStatus.BLOCKED, EvidenceClass.BLOCKAGE,
                "The executable exists but permission denied the version check.",
                command, executable=executable, error_code="permission_denied",
            )
        except OSError as exc:
            self.circuit_breaker.failure(spec.command)
            return ToolDiagnostic(
                spec.name, ToolStatus.ERROR, EvidenceClass.BLOCKAGE,
                f"The version check could not start: {type(exc).__name__}.",
                command, executable=executable, error_code="execution_error",
            )
        if result.exit_code != 0:
            self.circuit_breaker.failure(spec.command)
            details = _excerpt(result.stdout, result.stderr)
            suffix = f" Output: {details}" if details else ""
            return ToolDiagnostic(
                spec.name, ToolStatus.ERROR, EvidenceClass.PROOF,
                f"The executable returned non-zero exit code {result.exit_code}.{suffix}",
                command, executable=executable, exit_code=result.exit_code,
                error_code="nonzero_exit",
            )
        self.circuit_breaker.success(spec.command)
        version = _excerpt(result.stdout, result.stderr)
        if version:
            return ToolDiagnostic(
                spec.name, ToolStatus.INSTALLED, EvidenceClass.PROOF,
                "The executable was found and its version command succeeded.",
                command, executable=executable, version=version, exit_code=0,
            )
        return ToolDiagnostic(
            spec.name, ToolStatus.INSTALLED, EvidenceClass.INFERENCE,
            "The executable responded successfully, but returned no version text.",
            command, executable=executable, exit_code=0,
        )

    def diagnose(self, specs: Iterable[ToolSpec] = DEFAULT_TOOL_SPECS) -> DiagnosticReport:
        bounded = tuple(specs)
        if not 1 <= len(bounded) <= 64:
            raise ContractError("between 1 and 64 tool specs are required")
        return DiagnosticReport.create(self.check(spec) for spec in bounded)

