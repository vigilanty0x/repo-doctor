from __future__ import annotations

import unittest

from ai_setup_doctor.models import (
    ContractError, DiagnosticReport, EvidenceClass, ToolDiagnostic, ToolStatus, canonical_json, sha256_json,
)

from helpers import diagnostic


class ToolDiagnosticTests(unittest.TestCase):
    def test_round_trip_all_fields(self) -> None:
        value = diagnostic()
        self.assertEqual(ToolDiagnostic.from_dict(value.to_dict()), value)

    def test_installed_cannot_have_error(self) -> None:
        with self.assertRaises(ContractError):
            ToolDiagnostic("Git", ToolStatus.INSTALLED, EvidenceClass.PROOF, "bad", ("git",), error_code="bad")

    def test_blocked_requires_error(self) -> None:
        with self.assertRaises(ContractError):
            ToolDiagnostic("Git", ToolStatus.BLOCKED, EvidenceClass.BLOCKAGE, "bad", ("git",))

    def test_error_requires_error(self) -> None:
        with self.assertRaises(ContractError):
            ToolDiagnostic("Git", ToolStatus.ERROR, EvidenceClass.PROOF, "bad", ("git",))

    def test_blockage_cannot_be_installed(self) -> None:
        with self.assertRaises(ContractError):
            ToolDiagnostic("Git", ToolStatus.INSTALLED, EvidenceClass.BLOCKAGE, "bad", ("git",))

    def test_empty_tool_rejected(self) -> None:
        with self.assertRaises(ContractError):
            ToolDiagnostic("", ToolStatus.MISSING, EvidenceClass.PROOF, "missing", ("git",))

    def test_empty_summary_rejected(self) -> None:
        with self.assertRaises(ContractError):
            ToolDiagnostic("Git", ToolStatus.MISSING, EvidenceClass.PROOF, "", ("git",))

    def test_empty_command_rejected(self) -> None:
        with self.assertRaises(ContractError):
            ToolDiagnostic("Git", ToolStatus.MISSING, EvidenceClass.PROOF, "missing", ())

    def test_unknown_field_rejected(self) -> None:
        value = diagnostic().to_dict()
        value["surprise"] = True
        with self.assertRaises(ContractError):
            ToolDiagnostic.from_dict(value)


class DiagnosticReportTests(unittest.TestCase):
    def test_sorting_is_deterministic(self) -> None:
        first = DiagnosticReport.create([diagnostic("Python"), diagnostic("Git")])
        second = DiagnosticReport.create([diagnostic("Git"), diagnostic("Python")])
        self.assertEqual(first.report_id, second.report_id)
        self.assertEqual([item.tool for item in first.diagnostics], ["Git", "Python"])

    def test_summary_counts_each_status(self) -> None:
        report = DiagnosticReport.create([
            diagnostic("One"), diagnostic("Two", ToolStatus.MISSING), diagnostic("Three", ToolStatus.BLOCKED)
        ])
        self.assertEqual(report.summary, {"installed": 1, "missing": 1, "blocked": 1, "error": 0})

    def test_duplicate_names_rejected_case_insensitively(self) -> None:
        with self.assertRaises(ContractError):
            DiagnosticReport.create([diagnostic("Git"), diagnostic("git")])

    def test_empty_report_rejected(self) -> None:
        with self.assertRaises(ContractError):
            DiagnosticReport.create([])

    def test_round_trip(self) -> None:
        report = DiagnosticReport.create([diagnostic()])
        self.assertEqual(DiagnosticReport.from_dict(report.to_dict()), report)

    def test_tampered_report_id_rejected(self) -> None:
        value = DiagnosticReport.create([diagnostic()]).to_dict()
        value["report_id"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "report_id"):
            DiagnosticReport.from_dict(value)

    def test_tampered_summary_rejected(self) -> None:
        value = DiagnosticReport.create([diagnostic()]).to_dict()
        value["summary"]["installed"] = 0
        with self.assertRaisesRegex(ContractError, "summary"):
            DiagnosticReport.from_dict(value)

    def test_unknown_report_field_rejected(self) -> None:
        value = DiagnosticReport.create([diagnostic()]).to_dict()
        value["host"] = "synthetic"
        with self.assertRaises(ContractError):
            DiagnosticReport.from_dict(value)

    def test_changed_evidence_changes_identity(self) -> None:
        installed = DiagnosticReport.create([diagnostic()])
        missing = DiagnosticReport.create([diagnostic(status=ToolStatus.MISSING)])
        self.assertNotEqual(installed.report_id, missing.report_id)

    def test_canonical_json_is_stable(self) -> None:
        self.assertEqual(canonical_json({"b": 2, "a": 1}), '{"a":1,"b":2}')
        self.assertEqual(sha256_json({"a": 1}), sha256_json({"a": 1}))


if __name__ == "__main__":
    unittest.main()

