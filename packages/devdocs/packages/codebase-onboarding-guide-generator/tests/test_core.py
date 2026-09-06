import unittest

from codebase_onboarding_guide_generator import evaluate

GOOD = {"project": "sample", "entrypoints": ["src/app.py"], "commands": ["python -m app"], "tests": ["python -m unittest"]}


class ContractTests(unittest.TestCase):
    def test_valid_record_renders_guide(self):
        result = evaluate(GOOD)
        self.assertEqual(result["status"], "passed")
        self.assertIn("# sample", result["guide_markdown"])

    def test_markdown_metacharacters_are_escaped(self):
        record = {**GOOD, "project": "[unsafe](url)", "entrypoints": ["*entry*"]}
        rendered = evaluate(record)["guide_markdown"]
        self.assertIn(r"\[unsafe\]\(url\)", rendered)
        self.assertIn(r"\*entry\*", rendered)

    def test_code_spans_choose_safe_fence(self):
        rendered = evaluate({**GOOD, "commands": ["python `demo`"]})["guide_markdown"]
        self.assertIn("`` python `demo` ``", rendered)

    def test_newline_injection_fails_closed(self):
        self.assertEqual(evaluate({**GOOD, "project": "safe\n# injected"})["status"], "failed")

    def test_aggregate_bound_fails_closed(self):
        self.assertEqual(evaluate({**GOOD, "commands": ["x" * 40_000]})["status"], "failed")

    def test_non_object_is_structured_failure(self):
        self.assertEqual(evaluate([])["status"], "failed")

    def test_missing_field_blocks_and_result_is_deterministic(self):
        self.assertEqual(evaluate({})["status"], "blocked")
        self.assertEqual(evaluate(GOOD), evaluate(dict(reversed(list(GOOD.items())))))


if __name__ == "__main__":
    unittest.main()
