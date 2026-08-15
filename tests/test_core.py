import unittest
from backup_verifier import verify,probe
X={"a":{"sha256":"a"*64,"size":1}}
class Tests(unittest.TestCase):
 def test_verify(self):self.assertTrue(verify(X,X)["verified"])
 def test_missing(self):self.assertFalse(verify(X,{})["verified"])
 def test_mismatch(self):self.assertFalse(verify(X,{"a":{"sha256":"b"*64,"size":1}})["verified"])
 def test_probe(self):self.assertTrue(probe()["ok"])
if __name__=="__main__":unittest.main()
