"""Safe JSON input and atomic report output."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .models import ContractError, DiagnosticReport, canonical_json


def load_report(path: Path) -> DiagnosticReport:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"report could not be read: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("report root must be an object")
    return DiagnosticReport.from_dict(value)


def write_report(path: Path, report: DiagnosticReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(canonical_json(report.to_dict()) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise

