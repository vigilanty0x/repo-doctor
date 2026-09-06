import copy
import json
import unittest
from pathlib import Path

from scripts.check_devdocs_integration import validate

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / "DEVDOCS.json").read_text(encoding="utf-8"))


class DevDocsIntegrationTests(unittest.TestCase):
    def candidate(self):
        return copy.deepcopy(BASELINE)

    def assert_rejected(self, mutate, fragment):
        candidate = self.candidate()
        mutate(candidate)
        errors = validate(candidate, ROOT)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_baseline_is_valid(self):
        self.assertEqual(validate(BASELINE, ROOT), [])

    def test_counterproof_rejects_missing_module(self):
        self.assert_rejected(lambda data: data["modules"].pop(), "exactly seven")

    def test_counterproof_rejects_duplicate_module(self):
        def mutate(data):
            data["modules"][1]["repository"] = data["modules"][0]["repository"]
        self.assert_rejected(mutate, "module identities")

    def test_counterproof_rejects_integration_order_drift(self):
        def mutate(data):
            data["experience"][0], data["experience"][1] = data["experience"][1], data["experience"][0]
        self.assert_rejected(mutate, "seven-step integration order")

    def test_counterproof_rejects_wrong_module_role(self):
        self.assert_rejected(
            lambda data: data["modules"][0].__setitem__("role", "publish-document"),
            "canonical integration journey",
        )

    def test_counterproof_rejects_lost_history_evidence(self):
        self.assert_rejected(
            lambda data: data["modules"][2].__setitem__("historyPreserved", False),
            "historyPreserved=true",
        )

    def test_counterproof_rejects_tree_mismatch(self):
        self.assert_rejected(
            lambda data: data["modules"][3].__setitem__("treeMatch", False),
            "treeMatch=true",
        )

    def test_counterproof_rejects_automatic_archive(self):
        self.assert_rejected(
            lambda data: data["archive"].__setitem__("automatic", True),
            "never be automatic",
        )

    def test_counterproof_rejects_missing_human_gate(self):
        self.assert_rejected(
            lambda data: data["archive"].__setitem__(
                "required", [gate for gate in data["archive"]["required"] if gate != "humanApproval"]
            ),
            "archive gates",
        )


if __name__ == "__main__":
    unittest.main()
