import sqlite3
def diagnose(connection,required_tables=(),required_indexes=()):
 integrity=connection.execute("PRAGMA integrity_check").fetchone()[0]
 fk=connection.execute("PRAGMA foreign_key_check").fetchall()
 objects={row[0]:row[1] for row in connection.execute("SELECT name,type FROM sqlite_master WHERE type IN ('table','index')")}
 issues=[]
 if integrity!="ok": issues.append("integrity")
 if fk: issues.append("foreign_keys")
 issues += [f"missing_table:{x}" for x in required_tables if objects.get(x)!="table"]
 issues += [f"missing_index:{x}" for x in required_indexes if objects.get(x)!="index"]
 return {"status":"healthy" if not issues else "blocked","integrity":integrity,"foreign_key_violations":len(fk),"issues":issues}
def run(data):
 c=sqlite3.connect(data.get("path",":memory:"))
 try: return diagnose(c,data.get("required_tables",()),data.get("required_indexes",()))
 finally: c.close()

