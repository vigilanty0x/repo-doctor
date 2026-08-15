import sqlite3,unittest
from sqlite_health_doctor.core import diagnose
class T(unittest.TestCase):
 def setUp(self): self.c=sqlite3.connect(":memory:"); self.c.execute("create table x(id integer)")
 def tearDown(self): self.c.close()
 def test_ok(self): self.assertEqual(diagnose(self.c,["x"])["status"],"healthy")
 def test_missing_table(self): self.assertEqual(diagnose(self.c,["y"])["status"],"blocked")
 def test_missing_index(self): self.assertIn("missing_index:i",diagnose(self.c,required_indexes=["i"])["issues"])
 def test_integrity(self): self.assertEqual(diagnose(self.c)["integrity"],"ok")
 def test_count(self): self.assertEqual(diagnose(self.c)["foreign_key_violations"],0)
if __name__=="__main__": unittest.main()

