"""Small public Python API."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Callable

from .checks import DEFAULT_TOOL_SPECS, CircuitBreaker, Doctor, Executor, ToolSpec
from .models import DiagnosticReport


def diagnose(
    specs: Iterable[ToolSpec] = DEFAULT_TOOL_SPECS,
    *,
    finder: Callable[[str], str | None] | None = None,
    executor: Executor | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> DiagnosticReport:
    """Diagnose a bounded set of executables and return schema 1.0 evidence."""

    options = {"executor": executor, "circuit_breaker": circuit_breaker}
    if finder is not None:
        options["finder"] = finder
    return Doctor(**options).diagnose(specs)  # type: ignore[arg-type]

