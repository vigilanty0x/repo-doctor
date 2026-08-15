import hashlib,json,re
def find(records,fields):
 if len(records)>100000 or not fields: raise ValueError("bounded input")
 exact={}; normalized={}
 for row in records:
  raw={k:row.get(k) for k in fields}; norm={k:re.sub(r"\s+"," ",str(row.get(k,"")).strip().casefold()) for k in fields}
  for target,value in ((exact,raw),(normalized,norm)):
   key=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest(); target.setdefault(key,[]).append(row["id"])
 groups=lambda d:[sorted(v) for v in d.values() if len(v)>1]
 return {"exact":groups(exact),"normalized":groups(normalized)}
def run(data): return find(**data)

