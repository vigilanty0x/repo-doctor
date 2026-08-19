import unittest

from dependency_drift_reporter import evaluate

GOOD = {"manifest": {"python": "3.12", "tool": "1.0"}, "installed": {"python": "3.12", "tool": "1.0"}}


class ContractTests(unittest.TestCase):
    def test_matching_maps_pass(self):
        result = evaluate(GOOD)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["drift_report"]["drift"], [])

    def test_failed_result_preserves_structured_version_drift(self):
        result = evaluate({"manifest": {"python": "3.12"}, "installed": {"python": "3.11"}})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["drift_report"]["drift"], [{"name": "python", "declared": "3.12", "installed": "3.11"}])

    def test_failed_result_preserves_missing_and_extra_dependencies(self):
        result = evaluate({"manifest": {"a": "1"}, "installed": {"b": "2"}})
        self.assertEqual(result["drift_report"]["drift_count"], 2)
        self.assertIn({"name": "a", "declared": "1", "installed": None}, result["drift_report"]["drift"])
        self.assertIn({"name": "b", "declared": None, "installed": "2"}, result["drift_report"]["drift"])

    def test_invalid_map_does_not_create_report(self):
        result = evaluate({"manifest": {"a": ""}, "installed": {"a": "1"}})
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["drift_report"])

    def test_nonfinite_and_non_object_fail_closed(self):
        self.assertEqual(evaluate({"manifest": {"a": float("nan")}, "installed": {"a": "1"}})["status"], "failed")
        self.assertEqual(evaluate(None)["status"], "failed")

    def test_missing_field_blocks(self):
        self.assertEqual(evaluate({})["status"], "blocked")

    def test_result_is_deterministic(self):
        self.assertEqual(evaluate(GOOD), evaluate(dict(reversed(list(GOOD.items())))))


if __name__ == "__main__":
    unittest.main()
