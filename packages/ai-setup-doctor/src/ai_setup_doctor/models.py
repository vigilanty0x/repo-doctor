"""Validated, machine-readable diagnostic contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "1.0"
MAX_TOOLS = 64


class ContractError(ValueError):
    """Raised when a diagnostic document violates the public contract."""


class ToolStatus(StrEnum):
    INSTALLED = "installed"
    MISSING = "missing"
    BLOCKED = "blocked"
    ERROR = "error"


class EvidenceClass(StrEnum):
    PROOF = "proof"
    INFERENCE = "inference"
    BLOCKAGE = "blockage"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _bounded_text(label: str, value: str | None, limit: int) -> None:
    if value is not None and (not isinstance(value, str) or len(value) > limit):
        raise ContractError(f"{label} must be a string of at most {limit} characters")


@dataclass(frozen=True, slots=True)
class ToolDiagnostic:
    tool: str
    status: ToolStatus
    evidence_class: EvidenceClass
    summary: str
    checked_command: tuple[str, ...]
    executable: str | None = None
    version: str | None = None
    exit_code: int | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        _bounded_text("tool", self.tool, 64)
        _bounded_text("summary", self.summary, 512)
        _bounded_text("executable", self.executable, 1024)
        _bounded_text("version", self.version, 512)
        _bounded_text("error_code", self.error_code, 64)
        if not self.tool or not self.summary:
            raise ContractError("tool and summary must not be empty")
        if not 1 <= len(self.checked_command) <= 16:
            raise ContractError("checked_command must contain between 1 and 16 items")
        if any(not isinstance(item, str) or not item or len(item) > 256 for item in self.checked_command):
            raise ContractError("checked_command contains an invalid item")
        if self.status is ToolStatus.INSTALLED and self.error_code is not None:
            raise ContractError("installed diagnostics cannot carry an error_code")
        if self.status in {ToolStatus.BLOCKED, ToolStatus.ERROR} and not self.error_code:
            raise ContractError("blocked and error diagnostics require an error_code")
        if self.evidence_class is EvidenceClass.BLOCKAGE and self.status is ToolStatus.INSTALLED:
            raise ContractError("a blockage cannot be reported as installed")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        result["evidence_class"] = self.evidence_class.value
        result["checked_command"] = list(self.checked_command)
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ToolDiagnostic":
        allowed = {
            "tool", "status", "evidence_class", "summary", "checked_command",
            "executable", "version", "exit_code", "error_code",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ContractError(f"unknown diagnostic fields: {sorted(unknown)}")
        try:
            return cls(
                tool=value["tool"],
                status=ToolStatus(value["status"]),
                evidence_class=EvidenceClass(value["evidence_class"]),
                summary=value["summary"],
                checked_command=tuple(value["checked_command"]),
                executable=value.get("executable"),
                version=value.get("version"),
                exit_code=value.get("exit_code"),
                error_code=value.get("error_code"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractError(f"invalid diagnostic: {exc}") from exc


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    schema_version: str
    report_id: str
    diagnostics: tuple[ToolDiagnostic, ...]
    summary: Mapping[str, int]

    @classmethod
    def create(cls, diagnostics: Iterable[ToolDiagnostic]) -> "DiagnosticReport":
        ordered = tuple(sorted(diagnostics, key=lambda item: item.tool.casefold()))
        if not 1 <= len(ordered) <= MAX_TOOLS:
            raise ContractError(f"a report requires between 1 and {MAX_TOOLS} diagnostics")
        names = [item.tool.casefold() for item in ordered]
        if len(names) != len(set(names)):
            raise ContractError("tool names must be unique")
        summary = {status.value: sum(item.status is status for item in ordered) for status in ToolStatus}
        identity = {
            "schema_version": SCHEMA_VERSION,
            "diagnostics": [item.to_dict() for item in ordered],
            "summary": summary,
        }
        return cls(SCHEMA_VERSION, sha256_json(identity), ordered, summary)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "report_id": self.report_id,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "summary": dict(self.summary),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DiagnosticReport":
        if set(value) != {"schema_version", "report_id", "diagnostics", "summary"}:
            raise ContractError("report fields do not match schema 1.0")
        if value["schema_version"] != SCHEMA_VERSION:
            raise ContractError(f"unsupported schema_version: {value['schema_version']!r}")
        if not isinstance(value["diagnostics"], list):
            raise ContractError("diagnostics must be a list")
        report = cls.create(ToolDiagnostic.from_dict(item) for item in value["diagnostics"])
        if value["report_id"] != report.report_id:
            raise ContractError("report_id does not match report content")
        if value["summary"] != report.summary:
            raise ContractError("summary does not match diagnostics")
        return report

