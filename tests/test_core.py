import hashlib,unittest
from migration_verifier.core import verify
def m(v,sql): return {"version":v,"sql":sql,"sha256":hashlib.sha256(sql.encode()).hexdigest()}
class T(unittest.TestCase):
 def test_ok(self): self.assertEqual(verify([m(1,"create table x(id);")])["status"],"verified")
 def test_table(self): self.assertIn("x",verify([m(1,"create table x(id);")])["tables"])
 def test_order(self): self.assertEqual(verify([m(2,"select 1;")])["reason"],"non_contiguous")
 def test_hash(self): x=m(1,"select 1;"); x["sha256"]="bad"; self.assertEqual(verify([x])["reason"],"checksum")
 def test_sql(self): self.assertEqual(verify([m(1,"bad sql")])["status"],"blocked")
if __name__=="__main__": unittest.main()

