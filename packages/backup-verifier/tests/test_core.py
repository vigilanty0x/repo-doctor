import unittest

from backup_verifier import probe, verify

X = {"a": {"sha256": "a" * 64, "size": 1}}


class Tests(unittest.TestCase):
    def test_truthful_metadata_claim(self):
        result = verify(X, X)
        self.assertTrue(result["verified"])
        self.assertEqual(result["verification_scope"], "metadata_only")
        self.assertEqual(result["claim"], "untrusted_expected_metadata_match")
        trusted = verify(X, X, expected_manifest_trusted=True)
        self.assertEqual(trusted["claim"], "trusted_expected_metadata_match")

    def test_missing_mismatch_unexpected(self):
        self.assertFalse(verify(X, {})["verified"])
        self.assertFalse(verify(X, {"a": {"sha256": "b" * 64, "size": 1}})["verified"])
        self.assertFalse(verify({}, X)["verified"])

    def test_strict_manifests(self):
        for manifest in ({"../a": X["a"]}, {"a": {"sha256": "A" * 64, "size": 1}},
                         {"a": {"sha256": "a" * 64, "size": True}}, [], None):
            self.assertFalse(verify(manifest, {})["verified"])
        self.assertFalse(verify(X, X, expected_manifest_trusted=1)["verified"])

    def test_probe(self):
        self.assertTrue(probe()["ok"])


if __name__ == "__main__":
    unittest.main()
