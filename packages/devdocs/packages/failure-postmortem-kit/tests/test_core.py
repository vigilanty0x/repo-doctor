import unittest

from failure_postmortem_kit import build, probe

SPEC = {"incident": "i", "impact": "x", "timeline": ["t"], "evidence": ["e"],
        "causes": ["c"], "actions": [{"owner": "o", "due": "d", "action": "a"}]}


class Tests(unittest.TestCase):
    def test_evidence_and_accountability_required(self):
        self.assertTrue(build(SPEC)["ok"])
        self.assertFalse(build({**SPEC, "evidence": []})["ok"])
        self.assertFalse(build({**SPEC, "actions": [{"action": "a"}]})["ok"])

    def test_safe_bounded_markdown(self):
        result = build({**SPEC, "incident": "<b># fake</b>"})
        self.assertNotIn("<b>", result["markdown"])
        self.assertIn("\\#", result["markdown"])
        self.assertFalse(build({**SPEC, "evidence": ["one\ntwo"]})["ok"])
        self.assertFalse(build({**SPEC, "causes": ["x"] * 101})["ok"])

    def test_action_schema_and_malformed_input(self):
        self.assertFalse(build({**SPEC, "actions": [{**SPEC["actions"][0], "extra": 1}]})["ok"])
        self.assertFalse(build({**SPEC, "actions": ["bad"]})["ok"])
        self.assertFalse(build(None)["ok"])

    def test_probe(self):
        self.assertTrue(probe()["ok"])


if __name__ == "__main__":
    unittest.main()
