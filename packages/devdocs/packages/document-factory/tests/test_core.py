import unittest

from document_factory import probe, render


class Tests(unittest.TestCase):
    def test_render_and_exact_fields(self):
        self.assertEqual(render("Hi {{name}}", {"name": "Ada"})["markdown"], "Hi Ada")
        self.assertFalse(render("{{x}}", {})["ok"])
        self.assertFalse(render("plain", {"x": 1})["ok"])

    def test_context_safe_values_and_template(self):
        result = render("# {{name}}", {"name": "<b># title</b>"})
        self.assertNotIn("<b>", result["markdown"])
        self.assertIn("\\#", result["markdown"])
        self.assertFalse(render("{{x}}", {"x": "line\nevil"})["ok"])
        self.assertFalse(render("<b>{{x}}</b>", {"x": "safe"})["ok"])
        self.assertFalse(render("{{x}}", {"x": "\ud800"})["ok"])

    def test_strict_integer_and_bounds(self):
        self.assertEqual(render("{{n}}", {"n": 12})["markdown"], "12")
        for value in (True, 1.5, 10 ** 20, None):
            self.assertFalse(render("{{n}}", {"n": value})["ok"])
        self.assertFalse(render("x", {}, True)["ok"])

    def test_probe(self):
        self.assertTrue(probe()["ok"])


if __name__ == "__main__":
    unittest.main()
