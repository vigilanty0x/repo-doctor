import copy
import hashlib
import json
import unittest

from event_log_explorer import evaluate

GOOD = {"stream": "run-1", "events": [{"sequence": 1, "type": "started"}, {"sequence": 2, "type": "completed"}]}


def chained_record():
    previous = "0" * 64
    events = []
    for sequence, kind in [(1, "started"), (2, "completed")]:
        item = {"sequence": sequence, "type": kind, "payload": {}, "previous_sha256": previous}
        digest = hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        events.append({**item, "event_sha256": digest})
        previous = digest
    return {"stream": "run-1", "events": events}, previous


class ContractTests(unittest.TestCase):
    def test_contiguous_events_are_structural_only(self):
        result = evaluate(GOOD)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["timeline"]["integrity"], "structural-only")
        self.assertFalse(result["timeline"]["authenticity_verified"])

    def test_chain_matches_separately_supplied_head(self):
        record, expected_head = chained_record()
        result = evaluate(record, expected_head_sha256=expected_head)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["timeline"]["integrity"], "chain-matched-expected-head")

    def test_tampered_payload_breaks_chain(self):
        record, expected_head = chained_record()
        record["events"][0]["payload"] = {"tampered": True}
        self.assertEqual(evaluate(record, expected_head_sha256=expected_head)["status"], "failed")

    def test_wrong_expected_head_fails(self):
        record, _ = chained_record()
        self.assertEqual(evaluate(record, expected_head_sha256="a" * 64)["status"], "failed")

    def test_expected_head_without_chain_and_embedded_head_fail(self):
        self.assertEqual(evaluate(GOOD, expected_head_sha256="a" * 64)["status"], "failed")
        self.assertEqual(evaluate({**GOOD, "expected_head_sha256": "a" * 64})["status"], "failed")

    def test_payload_bound_and_nonfinite_values_fail(self):
        oversized = copy.deepcopy(GOOD)
        oversized["events"][0]["payload"] = {"x": "y" * 9000}
        self.assertEqual(evaluate(oversized)["status"], "failed")
        self.assertEqual(evaluate({"stream": "s", "events": [{"sequence": 1, "type": "x", "payload": {"n": float("nan")}}]})["status"], "failed")

    def test_non_object_and_missing_field_fail_closed(self):
        self.assertEqual(evaluate(None)["status"], "failed")
        self.assertEqual(evaluate({})["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
