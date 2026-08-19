"""Command-line interface for diagnostics, replay verification, and probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from .checks import DEFAULT_TOOL_SPECS, Doctor
from .fixtures import FixtureEnvironment
from .io import load_report, write_report
from .journal import AppendOnlyJournal
from .models import ContractError
from .probes import functional_probe, liveness_probe, readiness_probe


def _emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-setup-doctor", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    diagnose = subparsers.add_parser("diagnose", help="run bounded executable checks")
    diagnose.add_argument("--fixture", type=Path, help="use a synthetic schema-1.0 fixture")
    diagnose.add_argument("--output", type=Path, help="atomically write the report")
    diagnose.add_argument("--journal", type=Path, help="append the report once to an idempotent journal")

    verify = subparsers.add_parser("verify", help="verify a report or journal")
    verify.add_argument("path", type=Path)
    verify.add_argument("--journal", action="store_true", help="verify newline-delimited journal events")

    probe = subparsers.add_parser("probe", help="run an operational probe")
    probe.add_argument("mode", choices=("liveness", "readiness", "functional"))

    subparsers.add_parser("inventory", help="show the bounded default tool inventory")
    demo = subparsers.add_parser("demo", help="write a reproducible, purely synthetic demonstration")
    demo.add_argument("directory", type=Path)
    return parser


def _doctor_for_fixture(path: Path) -> tuple[Doctor, tuple]:
    fixture = FixtureEnvironment.load(path)
    return Doctor(finder=fixture.finder, executor=fixture.executor), fixture.specs


def _demo_fixture() -> FixtureEnvironment:
    return FixtureEnvironment.from_dict({
        "schema_version": "1.0",
        "tools": [
            {
                "name": "Git", "command": "git", "version_args": ["--version"],
                "timeout_seconds": 0.2, "present": True,
                "behavior": {"kind": "success", "stdout": "git version 2.45.0"},
            },
            {
                "name": "Docker", "command": "docker", "version_args": ["--version"],
                "timeout_seconds": 0.2, "present": False,
                "behavior": {"kind": "success", "stdout": "unused"},
            },
            {
                "name": "Ollama", "command": "ollama", "version_args": ["--version"],
                "timeout_seconds": 0.2, "present": True,
                "behavior": {"kind": "nonzero", "stderr": "synthetic daemon unavailable", "exit_code": 7},
            },
        ],
    })


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "diagnose":
            if args.fixture:
                doctor, specs = _doctor_for_fixture(args.fixture)
                report = doctor.diagnose(specs)
            else:
                report = Doctor().diagnose()
            if args.output:
                write_report(args.output, report)
            appended = AppendOnlyJournal(args.journal).append(report) if args.journal else None
            result = report.to_dict()
            if appended is not None:
                result["journal_appended"] = appended
            _emit(result)
            return 0 if report.summary["blocked"] == 0 and report.summary["error"] == 0 else 2
        if args.command == "verify":
            if args.journal:
                events = AppendOnlyJournal(args.path).read()
                _emit({"valid": True, "kind": "journal", "events": len(events)})
            else:
                report = load_report(args.path)
                _emit({"valid": True, "kind": "report", "report_id": report.report_id})
            return 0
        if args.command == "probe":
            probes = {"liveness": liveness_probe, "readiness": readiness_probe, "functional": functional_probe}
            result = probes[args.mode]()
            _emit(result.to_dict())
            return 0 if result.healthy else 3
        if args.command == "inventory":
            _emit({
                "schema_version": "1.0",
                "tools": [
                    {"name": spec.name, "command": spec.command, "version_args": list(spec.version_args),
                     "timeout_seconds": spec.timeout_seconds}
                    for spec in DEFAULT_TOOL_SPECS
                ],
            })
            return 0
        if args.command == "demo":
            fixture = _demo_fixture()
            report = Doctor(finder=fixture.finder, executor=fixture.executor).diagnose(fixture.specs)
            report_path = args.directory / "report.json"
            journal_path = args.directory / "journal.jsonl"
            write_report(report_path, report)
            journal = AppendOnlyJournal(journal_path)
            first_append = journal.append(report)
            second_append = journal.append(report)
            _emit({
                "report": str(report_path), "journal": str(journal_path), "report_id": report.report_id,
                "first_append": first_append, "second_append": second_append,
                "journal_events": len(journal.read()), "summary": dict(report.summary),
            })
            return 0
        raise AssertionError("unreachable command")
    except ContractError as exc:
        _emit({"error": "contract_error", "message": str(exc), "success": False})
        return 4
    except OSError as exc:
        _emit({"error": "io_error", "message": str(exc), "success": False})
        return 5


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

