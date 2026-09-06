from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_assistance_manifest.io import ManifestLoadError, bundled_schema, dump_manifest, load_manifest


class IoTests(unittest.TestCase):
    def test_dump_is_sorted_and_has_final_newline(self) -> None:
        self.assertEqual(dump_manifest({"z": 1, "a": 2}), '{\n  "a": 2,\n  "z": 1\n}\n')

    def test_duplicate_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text('{"schema_version":"1.0","schema_version":"2.0"}', encoding="utf-8")
            with self.assertRaisesRegex(ManifestLoadError, "duplicate JSON key"):
                load_manifest(path)

    def test_non_object_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ManifestLoadError, "root must be"):
                load_manifest(path)

    def test_bundled_schema_is_valid_json(self) -> None:
        schema = json.loads(bundled_schema())
        self.assertEqual(schema["title"], "AI Assistance Manifest")


if __name__ == "__main__":
    unittest.main()

