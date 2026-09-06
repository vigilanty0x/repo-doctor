import unittest

from system_map_generator import generate, probe


class Tests(unittest.TestCase):
    def test_graph_uses_opaque_ids(self):
        result = generate({"nodes": [{"id": "public-id", "label": "API"}], "edges": []})
        self.assertTrue(result["ok"])
        self.assertIn("node_000", result["mermaid"])
        self.assertNotIn("public-id[", result["mermaid"])

    def test_context_safe_label(self):
        result = generate({"nodes": [{"id": "a", "label": "x\"] --> evil[\"y"}], "edges": []})
        self.assertTrue(result["ok"])
        self.assertIn("&quot;", result["mermaid"])
        self.assertIn("--&gt;", result["mermaid"])
        self.assertFalse(generate({"nodes": [{"id": "a", "label": "x\nevil"}], "edges": []})["ok"])

    def test_dangling_duplicate_and_malformed(self):
        self.assertFalse(generate({"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "b"}]})["ok"])
        self.assertFalse(generate({"nodes": [{"id": "a"}], "edges": [
            {"from": "a", "to": "a"}, {"from": "a", "to": "a"}]})["ok"])
        self.assertFalse(generate(None)["ok"])

    def test_probe(self):
        self.assertTrue(probe()["ok"])


if __name__ == "__main__":
    unittest.main()
