import hashlib,sqlite3
def verify(migrations):
 versions=[m["version"] for m in migrations]
 if versions!=list(range(1,len(versions)+1)): return {"status":"blocked","reason":"non_contiguous"}
 for m in migrations:
  if m.get("sha256")!=hashlib.sha256(m["sql"].encode()).hexdigest(): return {"status":"blocked","reason":"checksum"}
 c=sqlite3.connect(":memory:")
 try:
  c.execute("BEGIN")
  for m in migrations: c.executescript(m["sql"])
  tables=sorted(r[0] for r in c.execute("select name from sqlite_master where type='table'"))
  c.rollback(); return {"status":"verified","versions":versions,"tables":tables}
 except sqlite3.Error as e:
  c.rollback(); return {"status":"blocked","reason":"sql_error","error":type(e).__name__}
 finally: c.close()
def run(data): return verify(**data)

