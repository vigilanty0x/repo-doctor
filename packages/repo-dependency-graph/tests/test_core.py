import unittest

from repo_dependency_graph import graph, probe


class Tests(unittest.TestCase):
    def test_deterministic_topological_order(self):
        data = {"repositories": [{"name": "app", "dependencies": ["core"]},
                                  {"name": "core", "dependencies": []},
                                  {"name": "docs", "dependencies": []}]}
        result = graph(data)
        self.assertEqual(result["topological_order"], ["core", "app", "docs"])
        self.assertEqual(result["scope"], "declared_input_only")
        self.assertFalse(result["external_dependencies_verified"])

    def test_deterministic_cycle(self):
        data = {"repositories": [{"name": "b", "dependencies": ["a"]},
                                  {"name": "a", "dependencies": ["b"]}]}
        self.assertEqual(graph(data)["cycle"], ["a", "b", "a"])

    def test_unique_known_edges_and_strict_entries(self):
        self.assertFalse(graph({"repositories": [{"name": "a", "dependencies": ["b"]}]})["ok"])
        self.assertFalse(graph({"repositories": [{"name": "a", "dependencies": ["a", "a"]}]})["ok"])
        self.assertFalse(graph({"repositories": [{"name": "a", "dependencies": [[]]}]})["ok"])
        self.assertFalse(graph({"repositories": ["a"]})["ok"])
        self.assertFalse(graph(None)["ok"])

    def test_probe(self):
        self.assertTrue(probe()["ok"])


if __name__ == "__main__":
    unittest.main()
