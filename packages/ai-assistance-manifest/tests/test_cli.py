from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from ai_assistance_manifest.cli import main


class CliTests(unittest.TestCase):
    def test_init_validate_and_render(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "AI_ASSISTANCE.json"
            markdown = root / "AI_ASSISTANCE.md"
            (root / "tests").mkdir()
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["init", str(manifest)]), 0)
                self.assertEqual(
                    main(["validate", str(manifest), "--check-files", "--root", str(root)]),
                    0,
                )
                self.assertEqual(
                    main(
                        [
                            "render",
                            str(manifest),
                            "--output",
                            str(markdown),
                            "--check-files",
                            "--root",
                            str(root),
                        ]
                    ),
                    0,
                )
            self.assertIn("# AI Assistance Manifest", markdown.read_text(encoding="utf-8"))

    def test_init_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text("{}", encoding="utf-8")
            with redirect_stderr(StringIO()):
                self.assertEqual(main(["init", str(path)]), 2)
            self.assertEqual(path.read_text(encoding="utf-8"), "{}")

    def test_json_diagnostics_are_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text("{}", encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["validate", str(path), "--format", "json"]), 1)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["valid"])
            self.assertTrue(payload["diagnostics"])

    def test_schema_can_be_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "schema.json"
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["schema", "--output", str(path)]), 0)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["title"], "AI Assistance Manifest")


if __name__ == "__main__":
    unittest.main()

