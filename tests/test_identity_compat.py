from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys
import unittest

import repo_doctor
import repo_doctor_ai


ROOT = Path(__file__).resolve().parents[1]


class CanonicalIdentityTests(unittest.TestCase):
    def test_public_api_and_version_are_identical(self) -> None:
        self.assertEqual(repo_doctor.__version__, "0.3.0")
        self.assertEqual(repo_doctor.__version__, repo_doctor_ai.__version__)
        for name in repo_doctor_ai.__all__:
            self.assertIs(getattr(repo_doctor, name), getattr(repo_doctor_ai, name))

    def test_submodule_aliases_share_module_identity(self) -> None:
        for name in (
            "baseline", "cli", "config", "diffing", "io_utils", "journal",
            "models", "planning", "registry", "reporting", "rules",
            "sanitization", "sbom", "scanner",
        ):
            canonical = importlib.import_module(f"repo_doctor.{name}")
            legacy = importlib.import_module(f"repo_doctor_ai.{name}")
            self.assertIs(canonical, legacy)

    def test_canonical_module_cli_reports_source_version(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
        completed = subprocess.run(
            [sys.executable, "-m", "repo_doctor", "--version"],
            cwd=ROOT,
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "repo-doctor 0.3.0")


if __name__ == "__main__":
    unittest.main()
