from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from ai_setup_doctor.checks import Doctor
from ai_setup_doctor.fixtures import FixtureEnvironment
from ai_setup_doctor.journal import AppendOnlyJournal, event_for, parse_lines, validate_event
from ai_setup_doctor.models import ContractError, DiagnosticReport, ToolStatus, canonical_json

from helpers import diagnostic


def fixture_value(kind: str = "success", *, present: bool = True) -> dict:
    return {
        "schema_version": "1.0",
        "tools": [{
            "name": "Synthetic", "command": "synthetic", "version_args": ["--version"],
            "timeout_seconds": 0.1, "present": present,
            "behavior": {"kind": kind, "stdout": "synthetic 1.0", "exit_code": 9},
        }],
    }


class FixtureTests(unittest.TestCase):
    def diagnose(self, kind: str = "success", present: bool = True):
        fixture = FixtureEnvironment.from_dict(fixture_value(kind, present=present))
        return Doctor(finder=fixture.finder, executor=fixture.executor).diagnose(fixture.specs)

    def test_success_replay(self) -> None:
        self.assertEqual(self.diagnose().summary["installed"], 1)

    def test_missing_never_executes(self) -> None:
        fixture = FixtureEnvironment.from_dict(fixture_value(present=False))
        report = Doctor(finder=fixture.finder, executor=fixture.executor).diagnose(fixture.specs)
        self.assertEqual(report.summary["missing"], 1)
        self.assertEqual(fixture.executor.calls, [])

    def test_nonzero_replay(self) -> None:
        report = self.diagnose("nonzero")
        self.assertEqual(report.diagnostics[0].status, ToolStatus.ERROR)
        self.assertEqual(report.diagnostics[0].exit_code, 9)

    def test_timeout_replay(self) -> None:
        self.assertEqual(self.diagnose("timeout").diagnostics[0].status, ToolStatus.BLOCKED)

    def test_permission_replay(self) -> None:
        self.assertEqual(self.diagnose("permission_denied").diagnostics[0].error_code, "permission_denied")

    def test_execution_error_replay(self) -> None:
        self.assertEqual(self.diagnose("execution_error").diagnostics[0].error_code, "execution_error")

    def test_repeated_fixture_has_same_report_id(self) -> None:
        self.assertEqual(self.diagnose().report_id, self.diagnose().report_id)

    def test_unknown_fixture_field_rejected(self) -> None:
        value = fixture_value()
        value["account"] = "synthetic"
        with self.assertRaises(ContractError):
            FixtureEnvironment.from_dict(value)

    def test_unknown_behavior_rejected(self) -> None:
        value = fixture_value("magic")
        with self.assertRaises(ContractError):
            FixtureEnvironment.from_dict(value)

    def test_duplicate_command_rejected(self) -> None:
        value = fixture_value()
        value["tools"].append({**value["tools"][0], "name": "Other"})
        with self.assertRaises(ContractError):
            FixtureEnvironment.from_dict(value)

    def test_load_invalid_json_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ContractError):
                FixtureEnvironment.load(path)


class JournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "events.jsonl"
        self.journal = AppendOnlyJournal(self.path)
        self.report = DiagnosticReport.create([diagnostic()])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_first_append_writes_one_event(self) -> None:
        self.assertTrue(self.journal.append(self.report))
        self.assertEqual(len(self.journal.read()), 1)

    def test_duplicate_append_is_idempotent(self) -> None:
        self.assertTrue(self.journal.append(self.report))
        before = self.path.read_bytes()
        self.assertFalse(self.journal.append(self.report))
        self.assertEqual(self.path.read_bytes(), before)

    def test_distinct_report_appends(self) -> None:
        self.journal.append(self.report)
        second = DiagnosticReport.create([diagnostic(status=ToolStatus.MISSING)])
        self.assertTrue(self.journal.append(second))
        self.assertEqual(len(self.journal.read()), 2)

    def test_event_id_is_reproducible(self) -> None:
        self.assertEqual(event_for(self.report)["event_id"], event_for(self.report)["event_id"])

    def test_empty_missing_journal_is_valid(self) -> None:
        self.assertEqual(self.journal.read(), [])

    def test_truncated_line_rejected(self) -> None:
        self.path.write_text(canonical_json(event_for(self.report)), encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "newline"):
            self.journal.read()

    def test_invalid_json_rejected(self) -> None:
        self.path.write_text("not-json\n", encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "invalid JSON"):
            self.journal.read()

    def test_tampered_payload_rejected(self) -> None:
        event = event_for(self.report)
        event["payload"]["summary"]["installed"] = 0
        with self.assertRaises(ContractError):
            validate_event(event)

    def test_duplicate_lines_rejected(self) -> None:
        line = canonical_json(event_for(self.report)) + "\n"
        with self.assertRaisesRegex(ContractError, "duplicates"):
            parse_lines([line, line])

    def test_corrupt_journal_blocks_append(self) -> None:
        self.path.write_text("{}\n", encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(ContractError):
            self.journal.append(self.report)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

