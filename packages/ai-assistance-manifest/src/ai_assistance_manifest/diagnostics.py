"""Stable, machine-readable diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, order=True)
class Diagnostic:
    """One validation finding with a stable code."""

    code: str
    path: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

