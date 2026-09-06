from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_assistance_manifest.validation import validate_manifest

from helpers import valid_manifest


def codes(manifest: dict, **kwargs) -> set[str]:
    return {diagnostic.code for diagnostic in validate_manifest(manifest, **kwargs)}


class ValidationTests(unittest.TestCase):
    def test_template_is_valid(self) -> None:
        self.assertEqual(validate_manifest(valid_manifest()), [])

    def test_unsupported_version_fails_closed(self) -> None:
        manifest = valid_manifest()
        manifest["schema_version"] = "2.0"
        self.assertIn("AAM200", codes(manifest))

    def test_unknown_top_level_field_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["typo"] = True
        self.assertIn("AAM106", codes(manifest))

    def test_namespaced_extension_is_allowed(self) -> None:
        manifest = valid_manifest()
        manifest["x-example"] = {"value": 1}
        self.assertNotIn("AAM106", codes(manifest))

    def test_duplicate_model_id_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["models"].append(dict(manifest["models"][0]))
        self.assertIn("AAM202", codes(manifest))

    def test_unknown_model_reference_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["contributions"]["ai"][0]["model_ref"] = "missing"
        self.assertIn("AAM207", codes(manifest))

    def test_unknown_evidence_reference_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["contributions"]["ai"][0]["evidence_refs"] = ["missing"]
        self.assertIn("AAM208", codes(manifest))

    def test_parent_traversal_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["evidence"][0]["location"] = "../private.txt"
        self.assertIn("AAM303", codes(manifest))

    def test_absolute_path_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["evidence"][0]["location"] = "/etc/passwd"
        self.assertIn("AAM303", codes(manifest))

    def test_windows_absolute_path_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["evidence"][0]["location"] = "C:\\private\\report.txt"
        self.assertIn("AAM303", codes(manifest))

    def test_unsafe_artifact_path_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["contributions"]["ai"][0]["artifacts"] = ["../../private.py"]
        self.assertIn("AAM303", codes(manifest))

    def test_file_existence_check(self) -> None:
        manifest = valid_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIn("AAM304", codes(manifest, root=root, check_files=True))
            (root / "tests").mkdir()
            self.assertNotIn("AAM304", codes(manifest, root=root, check_files=True))

    def test_suspected_secret_is_rejected(self) -> None:
        manifest = valid_manifest()
        synthetic_key = "sk-" + "1234567890abcdefghijklmnop"
        manifest["limitations"].append(synthetic_key)
        self.assertIn("AAM401", codes(manifest))

    def test_non_http_url_evidence_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["evidence"][0].update({"type": "url", "location": "file:///tmp/report"})
        self.assertIn("AAM301", codes(manifest))

    def test_url_with_embedded_credentials_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["evidence"][0].update(
            {"type": "url", "location": "https://user:password@example.com/report"}
        )
        self.assertIn("AAM301", codes(manifest))

    def test_bad_commit_evidence_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["evidence"][0].update({"type": "commit", "location": "main"})
        self.assertIn("AAM302", codes(manifest))


if __name__ == "__main__":
    unittest.main()
