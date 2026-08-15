import unittest
from repo_dependency_graph import graph,probe
class T(unittest.TestCase):
 def test_graph(self):self.assertTrue(graph({"repositories":[{"name":"a","dependencies":[]}]})["acyclic"])
 def test_cycle(self):self.assertFalse(graph({"repositories":[{"name":"a","dependencies":["b"]},{"name":"b","dependencies":["a"]}]})["acyclic"])
 def test_unknown(self):self.assertFalse(graph({"repositories":[{"name":"a","dependencies":["b"]}]})["ok"])
 def test_probe(self):self.assertTrue(probe()["ok"])
if __name__=="__main__":unittest.main()
