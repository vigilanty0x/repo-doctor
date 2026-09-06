from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from ai_setup_doctor.cli import run
from ai_setup_doctor.io import load_report, write_report
from ai_setup_doctor.models import ContractError, DiagnosticReport
from ai_setup_doctor.probes import functional_probe, liveness_probe, readiness_probe

from helpers import diagnostic


def call_cli(arguments: list[str]) -> tuple[int, dict]:
    output = StringIO()
    with redirect_stdout(output):
        code = run(arguments)
    return code, json.loads(output.getvalue())


class ProbeTests(unittest.TestCase):
    def test_liveness(self) -> None:
        result = liveness_probe()
        self.assertTrue(result.healthy)
        self.assertEqual(result.mode, "liveness")

    def test_readiness(self) -> None:
        self.assertTrue(readiness_probe().healthy)

    def test_functional_control_and_counterproof(self) -> None:
        result = functional_probe()
        self.assertTrue(result.healthy)
        self.assertTrue(all(check["passed"] for check in result.checks))
        self.assertIn("failure_not_transformed_to_success", {check["name"] for check in result.checks})

    def test_functional_is_repeatable(self) -> None:
        self.assertEqual(functional_probe().to_dict(), functional_probe().to_dict())


class IoTests(unittest.TestCase):
    def test_atomic_report_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            report = DiagnosticReport.create([diagnostic()])
            write_report(path, report)
            self.assertEqual(load_report(path), report)

    def test_tampered_report_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            report = DiagnosticReport.create([diagnostic()]).to_dict()
            report["report_id"] = "bad"
            path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_report(path)


class CliTests(unittest.TestCase):
    def test_inventory_is_bounded(self) -> None:
        code, output = call_cli(["inventory"])
        self.assertEqual(code, 0)
        self.assertGreaterEqual(len(output["tools"]), 5)
        self.assertLessEqual(len(output["tools"]), 64)

    def test_probe_functional_exit_zero(self) -> None:
        code, output = call_cli(["probe", "functional"])
        self.assertEqual(code, 0)
        self.assertTrue(output["healthy"])

    def test_demo_is_idempotent_inside_one_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, output = call_cli(["demo", directory])
            self.assertEqual(code, 0)
            self.assertTrue(output["first_append"])
            self.assertFalse(output["second_append"])
            self.assertEqual(output["journal_events"], 1)
            self.assertTrue(Path(output["report"]).is_file())

    def test_verify_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            call_cli(["demo", directory])
            code, output = call_cli(["verify", str(Path(directory) / "report.json")])
            self.assertEqual(code, 0)
            self.assertTrue(output["valid"])

    def test_verify_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            call_cli(["demo", directory])
            code, output = call_cli(["verify", str(Path(directory) / "journal.jsonl"), "--journal"])
            self.assertEqual(code, 0)
            self.assertEqual(output["events"], 1)

    def test_invalid_report_returns_contract_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{}", encoding="utf-8")
            code, output = call_cli(["verify", str(path)])
            self.assertEqual(code, 4)
            self.assertFalse(output["success"])

    def test_fixture_failure_returns_two_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "fixture.json"
            report = Path(directory) / "report.json"
            fixture.write_text(json.dumps({
                "schema_version": "1.0",
                "tools": [{
                    "name": "Failure", "command": "failure", "version_args": ["--version"],
                    "timeout_seconds": 0.1, "present": True, "behavior": {"kind": "timeout"},
                }],
            }), encoding="utf-8")
            code, output = call_cli(["diagnose", "--fixture", str(fixture), "--output", str(report)])
            self.assertEqual(code, 2)
            self.assertEqual(output["summary"]["blocked"], 1)
            self.assertTrue(report.is_file())

    def test_duplicate_journal_append_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "fixture.json"
            journal = Path(directory) / "events.jsonl"
            fixture.write_text(json.dumps({
                "schema_version": "1.0",
                "tools": [{
                    "name": "Control", "command": "control", "version_args": ["--version"],
                    "timeout_seconds": 0.1, "present": True,
                    "behavior": {"kind": "success", "stdout": "control 1"},
                }],
            }), encoding="utf-8")
            first_code, first = call_cli(["diagnose", "--fixture", str(fixture), "--journal", str(journal)])
            second_code, second = call_cli(["diagnose", "--fixture", str(fixture), "--journal", str(journal)])
            self.assertEqual((first_code, second_code), (0, 0))
            self.assertTrue(first["journal_appended"])
            self.assertFalse(second["journal_appended"])


if __name__ == "__main__":
    unittest.main()

