"""Append-only, replay-safe evidence journal."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any, Iterable

from .models import ContractError, DiagnosticReport, canonical_json, sha256_json


JOURNAL_KIND = "diagnostic_report"


def event_for(report: DiagnosticReport) -> dict[str, Any]:
    identity = {"kind": JOURNAL_KIND, "report_id": report.report_id}
    return {
        "event_id": sha256_json(identity),
        "kind": JOURNAL_KIND,
        "report_id": report.report_id,
        "payload": report.to_dict(),
    }


def validate_event(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"event_id", "kind", "report_id", "payload"}:
        raise ContractError("journal event fields do not match schema 1.0")
    if value["kind"] != JOURNAL_KIND:
        raise ContractError("unsupported journal event kind")
    report = DiagnosticReport.from_dict(value["payload"])
    expected = event_for(report)
    if value != expected:
        raise ContractError("journal event identity does not match its payload")
    return expected


def parse_lines(lines: Iterable[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line.endswith("\n"):
            raise ContractError(f"journal line {line_number} is not newline-terminated")
        try:
            event = validate_event(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ContractError(f"journal line {line_number} is invalid JSON") from exc
        if event["event_id"] in seen:
            raise ContractError(f"journal line {line_number} duplicates an event_id")
        seen.add(event["event_id"])
        events.append(event)
    return events


class AppendOnlyJournal:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8", newline="") as handle:
                return parse_lines(handle)
        except OSError as exc:
            raise ContractError(f"journal could not be read: {exc}") from exc

    def append(self, report: DiagnosticReport) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event = event_for(report)
        try:
            with self.path.open("a+", encoding="utf-8", newline="") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                handle.seek(0)
                events = parse_lines(handle)
                if any(existing["event_id"] == event["event_id"] for existing in events):
                    return False
                handle.seek(0, os.SEEK_END)
                handle.write(canonical_json(event) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
                return True
        except OSError as exc:
            raise ContractError(f"journal could not be appended: {exc}") from exc

