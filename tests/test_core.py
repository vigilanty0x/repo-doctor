import unittest
from duplicate_finder.core import find
class T(unittest.TestCase):
 def test_exact(self): self.assertEqual(find([{"id":"1","x":"a"},{"id":"2","x":"a"}],["x"])["exact"],[["1","2"]])
 def test_normal(self): self.assertEqual(find([{"id":"1","x":" A "},{"id":"2","x":"a"}],["x"])["normalized"],[["1","2"]])
 def test_distinct(self): self.assertEqual(find([{"id":"1","x":"a"},{"id":"2","x":"b"}],["x"])["exact"],[])
 def test_multi(self): self.assertEqual(find([{"id":"1","x":"a","y":1},{"id":"2","x":"a","y":2}],["x","y"])["exact"],[])
 def test_fields(self):
  with self.assertRaises(ValueError): find([],[])
if __name__=="__main__": unittest.main()

