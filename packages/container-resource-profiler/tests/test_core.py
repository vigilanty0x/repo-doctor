import unittest

from container_resource_profiler import evaluate

GOOD = {"scenario": "startup", "cpu_percent": 32.5, "memory_mb": 128, "io_mb": 2, "network_mb": 1, "startup_ms": 900}


class ContractTests(unittest.TestCase):
    def test_valid_profile_is_labeled_supplied(self):
        result = evaluate(GOOD)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["profile"]["source"], "supplied-measurements")
        self.assertFalse(result["profile"]["observed_by_tool"])

    def test_boolean_and_nonfinite_numbers_fail(self):
        self.assertEqual(evaluate({**GOOD, "cpu_percent": True})["status"], "failed")
        for value in (float("nan"), float("inf"), float("-inf")):
            self.assertEqual(evaluate({**GOOD, "memory_mb": value})["status"], "failed")

    def test_cpu_bound_fails(self):
        self.assertEqual(evaluate({**GOOD, "cpu_percent": 100.01})["status"], "failed")

    def test_memory_and_startup_must_be_positive(self):
        self.assertEqual(evaluate({**GOOD, "memory_mb": 0})["status"], "failed")
        self.assertEqual(evaluate({**GOOD, "startup_ms": 0})["status"], "failed")

    def test_transfer_bounds_fail(self):
        self.assertEqual(evaluate({**GOOD, "io_mb": 1_000_000_001})["status"], "failed")
        self.assertEqual(evaluate({**GOOD, "network_mb": -1})["status"], "failed")

    def test_non_object_and_missing_field_fail_closed(self):
        self.assertEqual(evaluate([])["status"], "failed")
        self.assertEqual(evaluate({})["status"], "blocked")

    def test_result_is_deterministic(self):
        self.assertEqual(evaluate(GOOD), evaluate(dict(reversed(list(GOOD.items())))))


if __name__ == "__main__":
    unittest.main()
