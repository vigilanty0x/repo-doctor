import unittest

from ai_project_provenance_badge import evaluate

EVIDENCE = {"artifact_sha256": "a" * 64, "test_sha256": "b" * 64, "review_sha256": "c" * 64, "issuer": "release-job", "issued_at": "2026-08-15T00:00:00Z"}
GOOD = {"project": "sample", "assistance_level": "assisted", "supervision": "human-reviewed", "tests_passed": 12, "evidence_url": "https://Example.Invalid/evidence", "evidence": EVIDENCE}


class ContractTests(unittest.TestCase):
    def test_valid_badge_is_documented_not_verified(self):
        result = evaluate(GOOD)
        self.assertEqual(result["status"], "passed")
        self.assertIn("provenance-documented", result["badge_markdown"])
        self.assertFalse(result["provenance"]["verified"])
        self.assertIn("https://example.invalid/evidence", result["badge_markdown"])

    def test_url_credentials_are_rejected(self):
        credential_url = "https://" + "user:pass@" + "example.invalid/x"
        self.assertEqual(evaluate({**GOOD, "evidence_url": credential_url})["status"], "failed")

    def test_url_markdown_and_control_injection_are_rejected(self):
        self.assertEqual(evaluate({**GOOD, "evidence_url": "https://example.invalid/x)\n[evil](https://evil.invalid"})["status"], "failed")

    def test_url_requires_nonempty_https_host(self):
        self.assertEqual(evaluate({**GOOD, "evidence_url": "https:///path"})["status"], "failed")
        self.assertEqual(evaluate({**GOOD, "evidence_url": "http://example.invalid"})["status"], "failed")

    def test_evidence_requires_exact_digests(self):
        evidence = {**EVIDENCE, "artifact_sha256": "trust me"}
        self.assertEqual(evaluate({**GOOD, "evidence": evidence})["status"], "failed")
        self.assertEqual(evaluate({**GOOD, "evidence": {**EVIDENCE, "extra": "claim"}})["status"], "failed")

    def test_boolean_test_count_and_naive_time_fail(self):
        self.assertEqual(evaluate({**GOOD, "tests_passed": True})["status"], "failed")
        self.assertEqual(evaluate({**GOOD, "evidence": {**EVIDENCE, "issued_at": "2026-08-15T00:00:00"}})["status"], "failed")

    def test_non_object_and_missing_field_fail_closed(self):
        self.assertEqual(evaluate(None)["status"], "failed")
        self.assertEqual(evaluate({})["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
