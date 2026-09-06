import unittest

from runbook_builder import build, probe

SPEC = {"service": "demo", "trigger": "alarm", "owner": "team", "steps": ["inspect"],
        "verification": ["healthy"], "rollback": ["restore"]}


class Tests(unittest.TestCase):
    def test_build_and_required_recovery(self):
        self.assertTrue(build(SPEC)["ok"])
        self.assertFalse(build({**SPEC, "rollback": []})["ok"])
        self.assertFalse(build({**SPEC, "steps": []})["ok"])

    def test_safe_bounded_markdown(self):
        result = build({**SPEC, "service": "<b># fake</b>"})
        self.assertNotIn("<b>", result["markdown"])
        self.assertIn("\\#", result["markdown"])
        self.assertFalse(build({**SPEC, "steps": ["one\ntwo"]})["ok"])
        self.assertFalse(build({**SPEC, "steps": ["x"] * 101})["ok"])

    def test_malformed_does_not_crash(self):
        for value in (None, [], {**SPEC, "steps": [1]}, {**SPEC, "extra": 1}):
            self.assertFalse(build(value)["ok"])

    def test_probe(self):
        self.assertTrue(probe()["ok"])


if __name__ == "__main__":
    unittest.main()
