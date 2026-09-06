import unittest

from state_machine_visualizer import evaluate

GOOD = {"name": "job", "states": ["queued", "running", "done"], "initial": "queued", "transitions": [["queued", "running"], ["running", "done"]]}


class ContractTests(unittest.TestCase):
    def test_valid_record_uses_opaque_ids(self):
        rendered = evaluate(GOOD)["mermaid"]
        self.assertIn('state "queued" as state_0', rendered)
        self.assertIn("state_0 --> state_1", rendered)
        self.assertNotIn("queued --> running", rendered)

    def test_newline_and_control_injection_are_rejected(self):
        attack = {**GOOD, "states": ["queued", "done\n    [*] --> injected"], "transitions": [["queued", "done\n    [*] --> injected"]]}
        self.assertEqual(evaluate(attack)["status"], "failed")
        self.assertEqual(evaluate({**GOOD, "name": "x\x00y"})["status"], "failed")

    def test_quotes_are_escaped_in_label_not_identifier(self):
        record = {"name": "x", "states": ['a"b', "done"], "initial": 'a"b', "transitions": [['a"b', "done"]]}
        rendered = evaluate(record)["mermaid"]
        self.assertIn(r'"a\"b"', rendered)
        self.assertIn("state_0 --> state_1", rendered)

    def test_duplicate_transition_is_rejected(self):
        self.assertEqual(evaluate({**GOOD, "transitions": [["queued", "running"], ["queued", "running"]]})["status"], "failed")

    def test_orphan_state_is_rejected(self):
        self.assertEqual(evaluate({**GOOD, "transitions": [["queued", "running"]]})["status"], "failed")

    def test_label_and_aggregate_bounds_are_enforced(self):
        self.assertEqual(evaluate({**GOOD, "name": "x" * 201})["status"], "failed")

    def test_non_object_and_missing_field_fail_closed(self):
        self.assertEqual(evaluate([])["status"], "failed")
        self.assertEqual(evaluate({})["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
